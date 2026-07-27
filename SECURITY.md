# Security Policy

PhotonHash v0.4.0-shadow.1 is pre-consensus research software. It has not
received a published independent security audit and must not be treated as a
production cryptographic primitive or used to secure assets of value.

For implementation vulnerabilities, use GitHub's private vulnerability
reporting or open a draft security advisory after the repository is created.
Include the affected commit, platform, reproduction steps, and expected
impact. Do not publish an exploitable implementation issue before the
maintainer has had a reasonable opportunity to respond.

Cryptanalytic results about the public construction are the purpose of this
release and may be reported through a normal issue. Please include a
reproducible artifact and use the severity vocabulary in
`docs/adversarial-brief.md`.

There is no production security-support window for this experimental release.

The shadownet safety boundary is security-critical: shadow work must never
change Laser validation, chain selection, difficulty, or availability.
Privately report any path that violates that separation, triggers unbounded
matrix allocation from an unknown work message, escapes the two-parent
reference cache bound, or permits a stale-parent result to be treated as
current.

The historical v0.2.3 profile remains publicly falsified. Reporting that known
hardware-economic failure is not a new vulnerability.
