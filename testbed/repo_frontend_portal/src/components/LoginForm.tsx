/**
 * Login Form Component.
 * Initiates auth verification via defaultAuthClient.
 */

import React, { useState } from "react";
import { defaultAuthClient } from "../services/authClient";

export const LoginForm: React.FC = () => {
  const [tokenInput, setTokenInput] = useState("");
  const [status, setStatus] = useState<string>("");

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("Verifying session...");
    try {
      const res = await defaultAuthClient.verifyUserSession(tokenInput);
      setStatus(`Success: Authenticated as ${res.user_id}`);
    } catch (err: any) {
      setStatus(`Failed: ${err.message}`);
    }
  };

  return (
    <div className="login-container">
      <h2>OmniContext Portal Authentication</h2>
      <form onSubmit={handleVerify}>
        <input
          type="text"
          placeholder="Enter Auth Token"
          value={tokenInput}
          onChange={(e) => setTokenInput(e.target.value)}
        />
        <button type="submit">Verify Session</button>
      </form>
      {status && <p className="status-msg">{status}</p>}
    </div>
  );
};
