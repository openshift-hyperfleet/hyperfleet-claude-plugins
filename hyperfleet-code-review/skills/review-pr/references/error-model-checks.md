# Error Model Checks (Mechanical Passes)

Reference file for drift detection between the error model standard (`error-model.md`) and the mechanical passes in `/review-pr` that reference it (passes 1.D, 8.A, 8.B).

## Coverage Map

| Standard Section | Check(s) |
|-----------------|----------|
| Goals | N/A (informational) |
| Non-Goals | N/A (informational) |
| Reference Implementation | N/A (informational) |
| RFC 9457 Problem Details | N/A (not checked by mechanical passes) |
| Basic Structure | N/A (not checked by mechanical passes) |
| Standard Fields (RFC 9457) | N/A (not checked by mechanical passes) |
| HyperFleet Extension Fields | N/A (not checked by mechanical passes) |
| Complete Example | N/A (informational) |
| Problem Types | N/A (not checked by mechanical passes) |
| Type URI Format | N/A (not checked by mechanical passes) |
| Registered Problem Types | N/A (not checked by mechanical passes) |
| Error Code Format | N/A (not checked by mechanical passes) |
| Format | N/A (not checked by mechanical passes) |
| Error Categories | N/A (not checked by mechanical passes) |
| HTTP Status Code Mapping | N/A (not checked by mechanical passes) |
| Client Errors (4xx) | N/A (not checked by mechanical passes) |
| Server Errors (5xx) | N/A (not checked by mechanical passes) |
| Mapping Policy | N/A (not checked by mechanical passes) |
| Validation Errors | N/A (not checked by mechanical passes) |
| Single Validation Error | N/A (not checked by mechanical passes) |
| Multiple Validation Errors | N/A (not checked by mechanical passes) |
| Validation Constraint Types | N/A (not checked by mechanical passes) |
| Standard Error Codes | N/A (not checked by mechanical passes) |
| Validation Errors (VAL) | N/A (not checked by mechanical passes) |
| Authentication Errors (AUT) | N/A (not checked by mechanical passes) |
| Authorization Errors (AUZ) | N/A (not checked by mechanical passes) |
| Not Found Errors (NTF) | N/A (not checked by mechanical passes) |
| Conflict Errors (CNF) | N/A (not checked by mechanical passes) |
| Rate Limit Errors (LMT) | N/A (not checked by mechanical passes) |
| Internal Errors (INT) | N/A (not checked by mechanical passes) |
| Service Errors (SVC) | N/A (not checked by mechanical passes) |
| Error Wrapping and Propagation | Pass 1.D (error wrapping) |
| Internal Error Handling | Pass 1.D (wrapping context), Pass 8.B (log before sanitize) |
| Security Considerations | Pass 8.A (input sanitization), Pass 8.B (no system details in responses) |
| Component-Specific Guidelines | N/A (not checked by mechanical passes) |
| API Service | N/A (not checked by mechanical passes) |
| Sentinel | N/A (not checked by mechanical passes) |
| Adapters | N/A (not checked by mechanical passes) |
| Error Logging Integration | Pass 8.B (structured error log fields) |
| Example Error Responses | N/A (informational) |
| Validation Error | N/A (informational) |
| Resource Not Found | N/A (informational) |
| Version Conflict | N/A (informational) |
| Rate Limit Exceeded | N/A (informational) |
| Internal Server Error | N/A (informational) |
