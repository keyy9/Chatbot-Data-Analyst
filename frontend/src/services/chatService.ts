import { useChatStore } from "../store/chatStore";

export const chatService = {
  sendQuery: (sessionId: string, query: string) => {
    return useChatStore.getState().submitUserQuery(sessionId, query);
  },
  sendClarificationOption: (sessionId: string, option: string) => {
    return useChatStore.getState().submitClarificationAnswer(sessionId, option);
  },
  clearChat: (sessionId: string) => {
    useChatStore.getState().clearSessionMessages(sessionId);
  }
};
