import pathlib
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from check_module_abi import exports
from make_patches import transform


class LegacyTests(unittest.TestCase):
    def test_absolute_414_export_table(self):
        base = 0xffffff8008080000
        raw = bytearray(128)
        struct.pack_into('<QQQQ', raw, 16, base, base+80, base+4, base+84)
        struct.pack_into('<II', raw, 48, 0x12345678, 0x87654321)
        raw[80:88] = b'foo\0bar\0'
        symbols = {'_text':0, '__start___ksymtab':16, '__stop___ksymtab':48,
                   '__ksymtab_foo':16, '__ksymtab_bar':32, '__start___kcrctab':48,
                   '__kstrtab_foo':80, '__kstrtab_bar':84}
        with tempfile.TemporaryDirectory() as directory:
            image = pathlib.Path(directory)/'Image'; image.write_bytes(raw)
            mapping = pathlib.Path(directory)/'System.map'
            mapping.write_text(''.join(f'{base+offset:x} R {name}\n' for name,offset in symbols.items()))
            self.assertEqual(exports(image,mapping), {'foo':0x12345678,'bar':0x87654321})
            raw[16:48] = bytes(32); image.write_bytes(raw)
            self.assertEqual(exports(image,mapping), {'foo':0x12345678,'bar':0x87654321})
            raw[80:84] = b'bad\0'; image.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'name mismatch'):
                exports(image,mapping)

    def test_414_hooks_precede_argument_checks(self):
        fixtures = [('fs/exec.c', 'static int do_execveat_common(int fd)\n{\n\tint retval;\n\tif (IS_ERR(filename))\n\t\treturn PTR_ERR(filename);\n}\n', 'ksu_handle_execveat(&fd', 'if (IS_ERR(filename))'),
                    ('fs/open.c', 'SYSCALL_DEFINE3(faccessat, int, dfd)\n{\n\tint res;\n\tif (mode & ~S_IRWXO)\n\t\treturn -EINVAL;\n}\n', 'ksu_handle_faccessat(&dfd', 'if (mode & ~S_IRWXO)')]
        for path,source,call,check in fixtures:
            result = transform(path,source)
            self.assertEqual(result.count(call),1)
            self.assertLess(result.index(call),result.index(check))
