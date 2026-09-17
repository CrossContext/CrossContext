/**
 * Frontend Authentication Client.
 * Connects directly to Backend AuthCoreService endpoints.
 */

export interface AuthSession {
  token: string;
  userId: string;
  expiresAt: number;
}

export interface VerificationResult {
  status: string;
  userId?: string;
  version: string;
}

export class AuthClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl;
  }

  /**
   * [TARGET MIGRATION CANDIDATE]
   * Currently calls legacy v1 auth verification endpoint.
   */
  async verifySessionToken(token: string): Promise<VerificationResult> {
    const response = await fetch(`${this.baseUrl}/v1/auth/verify`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      }
    });

    if (!response.ok) {
      throw new Error(`Auth verification failed with status ${response.status}`);
    }

    return response.json();
  }

  /**
   * Request authentication token from backend service.
   */
  async loginWithCredentials(username: string, pass: string): Promise<string> {
    const response = await fetch(`${this.baseUrl}/v1/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password: pass })
    });

    const data = await response.json();
    return data.token;
  }
}

export const defaultAuthClient = new AuthClient();
