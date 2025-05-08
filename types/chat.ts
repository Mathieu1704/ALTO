export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: number;
  }
  
  export interface ChatState {
    messages: Message[];
    isRecording: boolean;
    isProcessing: boolean;
    phoneNumber: string;
    audioLevel: number;
    
    // Add missing method definitions
    setIsRecording: (isRecording: boolean) => void;
    setIsProcessing: (isProcessing: boolean) => void;
    setPhoneNumber: (phoneNumber: string) => void;
    setAudioLevel: (audioLevel: number) => void;
    addMessage: (message: Message) => void;
    clearMessages: () => void;
  }