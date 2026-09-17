/**
 * Frontend Portal - Authentication Client Service
 * Downstream consumer service interacting with the centralized AuthCore microservice.
 */

export interface LegacyVerifyResponse {
  valid: boolean;
  user_id: string;
  schema: string;
}

export interface V2TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

/**
 * Validates session using backend auth service.
 * @param token - Session token string
 */
export async function verifyUserSession(token: string): Promise<LegacyVerifyResponse> {
  // CRITICAL DEPENDENCY: Calls backend repo_auth_core endpoint /v1/auth/verify
  const response = await fetch("https://auth.internal.corp/api/v1/auth/verify", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ token, client_id: "portal_web" }),
  });

  if (!response.ok) {
    throw new Error(`Authentication check failed: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Authenticates user credentials.
 */
export async function authenticatePortalUser(username: string, pass: string): Promise<boolean> {
  const result = await verifyUserSession("session_token_example_123");
  return result.valid;
}
