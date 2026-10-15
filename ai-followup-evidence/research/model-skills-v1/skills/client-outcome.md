# Separate sensor action from client result

1. Read the sensor action and client evidence as separate observations.
2. Allowed leaves client success unknown unless independent result evidence supports it.
3. Blocked describes that sensor event. It does not establish what the whole application did afterward.
4. A process/socket receipt can support attribution when its time and tuple match. It does not prove communication success.
5. A client result must match the exact time, tuple and attempt supplied by the evidence adapter.
6. A successful retry does not rewrite the outcome of an earlier blocked attempt.
7. Leave intent and complete UDP delivery unresolved when the evidence cannot establish them.

Example: the sensor blocked attempt A, and a client receipt reports success for retry B. Preserve the block for A and scope success to B. Do not say the sensor block failed or every application request succeeded.
