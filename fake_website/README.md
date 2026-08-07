# CyberShield Safe Phishing-Simulation Fixture

This is a deliberately harmless training page for testing CyberShield. It is not an impersonation of a real company and it must not be modified to collect, submit, or store credentials.

## Why CyberShield should flag it

The page intentionally includes these safe-to-test signals:

- A password field submitted with `GET`.
- An OTP-style field.
- An external form action that points to the reserved, non-routable `example.invalid` domain.
- JavaScript that always calls `preventDefault()`, so the form cannot transmit data.

## Deployment

It can be deployed as a static Vercel project. Keep the visible training banner and `noindex, nofollow` directive. Never use it to collect real information or to impersonate an organization.
