/**
 * Pendo trackAgent integration for TheSuite AI Chat.
 *
 * Usage:
 *   import { sendChatMessage, trackUserReaction } from './pendo-track-agent.js';
 *
 *   // Send a message and automatically track prompt + agent_response
 *   const result = await sendChatMessage("/api/chat/", userInput, conversationId);
 *
 *   // Track feedback on a specific message
 *   trackUserReaction(result.pendoTracking, result.pendoTracking.responseMessageId, "positive");
 */

const PENDO_AGENT_ID = "M23t24_UsWdjKITadNNBLbx2m1Q";

/**
 * Send a chat message to the backend and fire pendo.trackAgent() for
 * both the "prompt" and "agent_response" events.
 *
 * @param {string} endpoint  - API URL (e.g. "/api/chat/")
 * @param {string} userInput - The user's message text
 * @param {string} conversationId - Session/conversation identifier
 * @param {object} [options]
 * @param {boolean} [options.suggestedPrompt] - Was this a suggested prompt?
 * @param {boolean} [options.fileUploaded]    - Was a file attached?
 * @returns {Promise<object>} The API response JSON
 */
async function sendChatMessage(endpoint, userInput, conversationId, options) {
  var suggestedPrompt = (options && options.suggestedPrompt) || false;
  var fileUploaded = (options && options.fileUploaded) || false;

  // --- Track prompt ---
  var promptMessageId = crypto.randomUUID();
  if (window.pendo && typeof window.pendo.trackAgent === "function") {
    window.pendo.trackAgent("prompt", {
      agentId: PENDO_AGENT_ID,
      conversationId: conversationId,
      messageId: promptMessageId,
      content: userInput,
      suggestedPrompt: suggestedPrompt,
      fileUploaded: fileUploaded,
    });
  }

  // --- Call backend ---
  var response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: userInput,
      conversationId: conversationId,
    }),
  });
  var data = await response.json();

  // --- Track agent response ---
  var tracking = data.pendoTracking || {};
  if (window.pendo && typeof window.pendo.trackAgent === "function") {
    window.pendo.trackAgent("agent_response", {
      agentId: PENDO_AGENT_ID,
      conversationId: tracking.conversationId || conversationId,
      messageId: tracking.responseMessageId || "agent_response_" + Date.now(),
      content: data.reply,
      modelUsed: tracking.modelUsed || "gemini-2.5-flash",
      toolsUsed: [],
    });
  }

  return data;
}

/**
 * Track a user reaction (thumbs up/down, retry, etc.) on a message.
 *
 * @param {object} pendoTracking  - The pendoTracking object from the API response
 * @param {string} messageId      - The messageId the reaction refers to
 * @param {"positive"|"negative"|"mixed"|"undo"|"retry"} reactionType
 */
function trackUserReaction(pendoTracking, messageId, reactionType) {
  if (window.pendo && typeof window.pendo.trackAgent === "function") {
    window.pendo.trackAgent("user_reaction", {
      agentId: PENDO_AGENT_ID,
      conversationId: pendoTracking.conversationId,
      messageId: messageId,
      content: reactionType,
    });
  }
}

// ES module exports (use <script type="module"> or a bundler)
export { sendChatMessage, trackUserReaction, PENDO_AGENT_ID };
