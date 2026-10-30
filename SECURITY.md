# Security

This demonstration has no authenticated backend. Do not store confidential information in browser notes, commit credentials or use outputs for automatic enforcement.

Report a suspected vulnerability privately through the repository maintainer's GitHub profile/contact channel. Do not include a credential or exploit data in a public issue. If a secret has been published, revoke it before removing the file; deleting a file does not remove Git history.

The supplied credential-pattern scan is a best-effort check, not a security certification. Review the actual staged diff before every public push. Model checkpoints should only be loaded from trusted sources; a hash proves file identity, not that arbitrary serialized content is safe.
