export function generateId(prefix: string) {
  const random = Math.random().toString(36).slice(2, 10);
  return `${prefix}_${random}`;
}

/** RFC 4122 UUID v4 for job ids and other stable public identifiers. */
export function randomUuid(): string {
  const cryptoRef = typeof globalThis !== "undefined" ? globalThis.crypto : undefined;
  if (cryptoRef && typeof cryptoRef.randomUUID === "function") {
    return cryptoRef.randomUUID();
  }
  throw new Error("randomUuid requires Web Crypto randomUUID (Node 19+ / modern runtimes).");
}
