export class ApiError extends Error {
  constructor(
    message,
    { code = "NETWORK_ERROR", status = 0, requestId = "" } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.requestId = requestId;
  }
}

export class StaleSessionError extends Error {
  constructor() {
    super("Session changed");
    this.name = "StaleSessionError";
  }
}

export const FRIENDLY_ERRORS = {
  LLM_REQUEST_TOO_LARGE: "The API request is too large. Select a document type or ask a narrower question.",
  LLM_RATE_LIMIT: "The API rate limit was reached. Wait before trying again.",
  LLM_AUTHENTICATION: "The backend API key was rejected. Check its configuration.",
  LLM_PERMISSION: "The configured model is not available to this API key.",
  LLM_REQUEST_REJECTED: "The API rejected the model or request format.",
  LLM_INVALID_OUTPUT: "The model returned an invalid structured answer. Try a more specific question.",
  LLM_OUTPUT_TRUNCATED: "The answer was cut short. Ask a shorter question.",
  LLM_TIMEOUT: "The model request timed out. Try a smaller request.",
  SUMMARY_TOO_LARGE: "Your records exceed the summary limit. Select a document type or narrow the question.",
  INVALID_CREDENTIALS: "That email and password don't match. Please try again.",
  EMAIL_EXISTS: "An account already uses this email. Sign in instead.",
  INVALID_TOKEN: "Your session has ended. Please sign in again.",
  DOCUMENT_NOT_FOUND: "This record is no longer available.",
  UPLOAD_TOO_LARGE: "This file is larger than the upload limit.",
  UNSUPPORTED_MEDIA: "Choose a PDF, TXT, or DOCX file.",
  MALFORMED_DOCUMENT:
    "We couldn't read this file. Try a text-based PDF, TXT, or DOCX.",
  EMPTY_DOCUMENT:
    "No readable text was found. Scanned documents need text recognition before upload.",
  EXTRACTION_LIMIT:
    "This document has too much content to process. Try a shorter file.",
  VALIDATION_ERROR: "Check the fields and try again.",
  DATABASE_UNAVAILABLE:
    "Your records are temporarily unavailable. Please try again shortly.",
  PRIVACY_UNAVAILABLE:
    "We couldn't prepare this record safely. Please try again shortly.",
  EMBEDDING_UNAVAILABLE:
    "Record processing is temporarily unavailable. Please try again shortly.",
  LLM_UNAVAILABLE:
    "The record assistant is temporarily unavailable. Please try again shortly.",
  RAG_TIMEOUT:
    "The assistant took too long to respond. Try a more specific question.",
};

export class ApiClient {
  constructor({
    fetchImpl = globalThis.fetch.bind(globalThis),
    onExpired = () => {},
  } = {}) {
    this.fetchImpl = fetchImpl;
    this.onExpired = onExpired;
    this.token = null;
    this.version = 0;
    this.controllers = new Set();
    this.expiryTimer = null;
  }
  setSession(token, expiresIn) {
    if (
      typeof token !== "string" ||
      !token ||
      !Number.isFinite(expiresIn) ||
      expiresIn <= 0
    ) {
      throw new ApiError("The sign-in response was invalid. Try again.");
    }
    this.clearSession();
    this.token = token;
    const version = this.version;
    this.expiryTimer = setTimeout(
      () => {
        if (version === this.version) this.onExpired();
      },
      Math.min(expiresIn * 1000, 2147483647),
    );
    this.expiryTimer.unref?.();
  }
  clearSession() {
    this.version += 1;
    this.token = null;
    clearTimeout(this.expiryTimer);
    this.expiryTimer = null;
    this.abortGroup();
  }
  abortGroup(group) {
    for (const item of this.controllers)
      if (!group || item.group === group) item.controller.abort();
  }
  async request(
    path,
    {
      method = "GET",
      body,
      auth = true,
      timeoutMs = 30000,
      group = "general",
    } = {},
  ) {
    if (auth && !this.token)
      throw new ApiError("Sign in to continue.", {
        code: "INVALID_TOKEN",
        status: 401,
      });
    const version = this.version,
      controller = new AbortController(),
      item = { controller, group };
    this.controllers.add(item);
    const timer = setTimeout(() => controller.abort("timeout"), timeoutMs);
    const headers = { Accept: "application/json" };
    if (auth) headers.Authorization = `Bearer ${this.token}`;
    const isForm = typeof FormData !== "undefined" && body instanceof FormData;
    if (body !== undefined && !isForm)
      headers["Content-Type"] = "application/json";
    try {
      const response = await this.fetchImpl(path, {
        method,
        headers,
        body:
          body === undefined ? undefined : isForm ? body : JSON.stringify(body),
        cache: "no-store",
        credentials: "omit",
        signal: controller.signal,
      });
      if (version !== this.version) throw new StaleSessionError();
      const data =
        response.status === 204
          ? null
          : await response.json().catch(() => null);
      if (version !== this.version) throw new StaleSessionError();
      if (!response.ok) {
        const code = data?.error?.code || "HTTP_ERROR";
        const error = new ApiError(
          FRIENDLY_ERRORS[code] ||
            "We couldn't complete that request. Please try again.",
          {
            code,
            status: response.status,
            requestId:
              data?.request_id || response.headers.get("x-request-id") || "",
          },
        );
        if (response.status === 401 && auth) this.onExpired();
        throw error;
      }
      if (data === null && response.status !== 204)
        throw new ApiError("The service returned an unreadable response.");
      return data;
    } catch (error) {
      if (version !== this.version && !(error instanceof ApiError))
        throw new StaleSessionError();
      if (error instanceof ApiError || error instanceof StaleSessionError)
        throw error;
      if (controller.signal.aborted)
        throw new ApiError(
          controller.signal.reason === "timeout"
            ? "This request took too long. Please try again."
            : "Request cancelled.",
          {
            code:
              controller.signal.reason === "timeout" ? "TIMEOUT" : "CANCELLED",
          },
        );
      throw new ApiError(
        "We can't reach the service. Check your connection and try again.",
      );
    } finally {
      clearTimeout(timer);
      this.controllers.delete(item);
    }
  }
}
