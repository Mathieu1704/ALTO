import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface SettingsState {
  isDarkTheme: boolean;
  enableNotifications: boolean;
  saveTranscripts: boolean;
  
  setIsDarkTheme: (isDarkTheme: boolean) => void;
  setEnableNotifications: (enableNotifications: boolean) => void;
  setSaveTranscripts: (saveTranscripts: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      isDarkTheme: true,
      enableNotifications: true,
      saveTranscripts: true,
      
      setIsDarkTheme: (isDarkTheme: boolean) => set({ isDarkTheme }),
      setEnableNotifications: (enableNotifications: boolean) => set({ enableNotifications }),
      setSaveTranscripts: (saveTranscripts: boolean) => set({ saveTranscripts }),
    }),
    {
      name: 'settings-storage',
      storage: createJSONStorage(() => AsyncStorage),
    }
  )
);