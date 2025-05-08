import { create } from 'zustand';
import { ChatState, Message } from '@/types/chat';

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isRecording: false,
  isProcessing: false,
  phoneNumber: '+32 487214255',
  audioLevel: 0,
  
  setIsRecording: (isRecording: boolean) => set({ isRecording }),
  setIsProcessing: (isProcessing: boolean) => set({ isProcessing }),
  setPhoneNumber: (phoneNumber: string) => set({ phoneNumber }),
  setAudioLevel: (audioLevel: number) => set({ audioLevel }),
  
  addMessage: (message: Message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  
  clearMessages: () => set({ messages: [] }),
}));