// Global namespaces that the classic browser scripts register. Classic scripts cannot use ES modules on file:// pages,
// so each file attaches its public functions to one global object, and the tests read them from there.

interface MysteryForgeAnswersApi {
  normalizeAnswer(text: string, language: string): string;
  answerHash(normalizedAnswer: string, salt: string): string;
  sha256Hex(text: string): string;
}

declare var MysteryForgeAnswers: MysteryForgeAnswersApi;
