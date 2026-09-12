"""Restore stock network message layouts from verified protobuf-c descriptors."""
import json
import pathlib
import re
import shutil
import tempfile
from project import ROOT, run, sha256

def protocol_directory(profile):
    if profile["platform"] == "sm8350":
        return ROOT / "compat/sm8350"
    name = "oneplus-8" if profile["id"] == "oneplus-8-pro" else profile["id"]
    return ROOT / "compat/sm8250" / name

def prepare(modules, profile):
    directory = protocol_directory(profile)
    schema = directory / "netlink_msg.proto"
    reflection = directory / "protocol-reflection.json"
    expected = json.loads(reflection.read_text())
    if not shutil.which("protoc-c"):
        raise RuntimeError("Install protobuf-c-compiler to restore the stock network protocol")
    destination = modules / "vendor/oplus/kernel/network/data_module/proto-src"
    with tempfile.TemporaryDirectory() as temporary:
        work = pathlib.Path(temporary)
        run("protoc-c", "--proto_path=" + str(schema.parent), "--c_out=" + str(work), schema.name)
        header = work / "netlink_msg.pb-c.h"
        text = header.read_text()
        # protoc-c 1.3 uses underscored struct tags; stock/public 1.4 uses these tags.
        # Preserve type names as well as layout for genksyms.
        for message in expected["messages"]:
            text = re.sub(r"\bstruct\s+_" + re.escape(message["c_name"]) + r"\b", "struct " + message["c_name"], text)
        include = "#include <protobuf-c/protobuf-c.h>"
        if text.count(include) != 1:
            raise ValueError("Unexpected protoc-c header format")
        header.write_text(text)
        generated = work / "netlink_msg.pb-c.c"
        cfi_safe = profile["platform"] == "sm8350"
        if cfi_safe:
            source = generated.read_text()
            callbacks = re.findall(r"\(ProtobufCMessageInit\)\s+(netlink__proto__[a-z0-9_]+__init)", source)
            declarations = dict(re.findall(r"void\s+(netlink__proto__[a-z0-9_]+__init)\s*\(\s*(Netlink__Proto__[A-Za-z0-9_]+)\s*\*\s*message\s*\)", text))
            if len(callbacks) != len(expected["messages"]) or len(set(callbacks)) != len(callbacks):
                raise ValueError("Unexpected protobuf initializer callbacks")
            wrappers = []
            for callback in callbacks:
                typename = declarations[callback]
                wrapper = callback + "_cfi"
                wrappers.append("static void " + wrapper + "(ProtobufCMessage *message)\n{\n  " + callback + "((" + typename + " *)message);\n}\n")
                source, count = re.subn(r"\(ProtobufCMessageInit\)\s+" + re.escape(callback) + r"\b", wrapper, source)
                if count != 1:
                    raise ValueError("Initializer callback replacement count differs")
            marker = '#include "netlink_msg.pb-c.h"'
            if source.count(marker) != 1:
                raise ValueError("Unexpected generated source include")
            generated.write_text(source.replace(marker, marker + "\n" + "\n".join(wrappers)))
        assertions = []
        groups = {"RequestMessage": "request_data", "ResponseMessage": "response_data", "NotifyMessage": "notify_data"}
        for message in expected["messages"]:
            name = message["c_name"]
            assertions.append('_Static_assert(sizeof(' + name + ') == ' + str(message["size"]) + ', "stock message size: ' + name + '");')
            for field in message["fields"]:
                member = field["name"].lower()
                assertions.append('_Static_assert(__builtin_offsetof(' + name + ', ' + member + ') == ' + str(field["offset"]) + ', "stock field offset: ' + name + '.' + member + '");')
                if field["quantifier"]:
                    quantifier = groups[message["short_name"]] + "_case" if field["flags"] & 4 else ("n_" if field["label"] == 2 else "has_") + member
                    assertions.append('_Static_assert(__builtin_offsetof(' + name + ', ' + quantifier + ') == ' + str(field["quantifier"]) + ', "stock quantifier offset");')
        with generated.open("a") as stream:
            stream.write("\n/* Validate the layouts against the original boot image. */\n" + "\n".join(assertions) + "\n")
        # Host and target are LP64; catch generated declaration/layout errors first.
        run("cc", "-std=gnu11", "-Werror=incompatible-pointer-types", "-fsyntax-only", str(generated))
        if cfi_safe:
            harness = work / "cfi_check.c"
            descriptors = [callback[:-len("__init")] + "__descriptor" for callback in callbacks]
            harness.write_text('#include "netlink_msg.pb-c.h"\n#include <stdlib.h>\n'
                + 'static const ProtobufCMessageDescriptor *const descriptors[] = {'
                + ','.join('&' + name for name in descriptors) + '};\n'
                + 'int main(void) { for (size_t i = 0; i < sizeof(descriptors)/sizeof(descriptors[0]); ++i) {'
                + 'volatile size_t selected = i; const ProtobufCMessageDescriptor *d = descriptors[selected];'
                + 'ProtobufCMessage *m = malloc(d->sizeof_message); if (!m) return 1;'
                + 'd->message_init(m); if (m->descriptor != d) return 2; free(m); } return 0; }\n')
            executable = work / "cfi_check"
            run("clang", "-O2", "-flto", "-fuse-ld=lld", "-fsanitize=cfi-icall", "-fvisibility=hidden",
                str(generated), str(harness), "-lprotobuf-c", "-o", str(executable))
            run(executable)
        header.write_text(text.replace(include, '#ifndef assert\n#define assert(condition) ((void)0)\n#endif\n#include "../comm_netlink/protobuf-c.h"'))
        for filename in ("netlink_msg.pb-c.h", "netlink_msg.pb-c.c"):
            shutil.copyfile(work / filename, destination / filename)
    return {"cfi_safe_initializers": cfi_safe, "schema_sha256": sha256(schema), "reflection_sha256": sha256(reflection),
            "stock_boot_sha256": expected["stock_boot_sha256"], "message_count": len(expected["messages"]),
            "origin": "recovered stock protobuf-c reflection metadata"}
