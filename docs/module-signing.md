# Original module signing trust

The first SM8250 builds preserved CONFIG_MODULE_SIG_FORCE=y but generated a new signing key. Matching exported symbol CRCs was insufficient: the original vendor modules could not be authenticated, leaving /proc/modules empty and SoundTrigger without a sound card. Android repeatedly restarted system_server.

On OnePlus 9R ColorOS LE2100_14.0.0.605(CN01), changing only the embedded public certificate restored temporary boot, loaded 34 modules and reached sys.boot_completed=1. The owner confirmed touch, sound, Wi-Fi and ReSukiSU manager detection.

Public certificates in compat/module-certificates are recovered from the exact registered stock kernel's system_certificate_list. No private signing keys are included. Source boot hashes are registered in each firmware profile. The build adds its matching PEM using CONFIG_SYSTEM_TRUSTED_KEYS while retaining CONFIG_MODULE_SIG_FORCE=y.

ColorOS and OxygenOS certificates differ even when configuration and symbol CRCs match. Reuse now checks the target firmware certificate and rejects kernels that do not contain it.

Packaging checks the actual certificate bytes embedded in Image. For the original SM8250 vendor/odm inventory it also cryptographically verifies each detached PKCS#7 signature against the pinned stock certificate. This complements, rather than replaces, CRC checks. OpenSSL -nointern pins the signer to the supplied certificate; -noverify skips CA/time policy, not content signature verification, matching direct kernel trust-anchor use.

SM8350 stock configurations do not enable CONFIG_MODULE_SIG, so this correction does not change their signature policy. Physical device validation remains separate from static verification.
