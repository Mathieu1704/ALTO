import { useChatStore } from '@/store/chat-store';
import { useSettingsStore } from '@/store/settings-store';
import { Audio } from 'expo-av';
import * as Haptics from 'expo-haptics';
import { useEffect, useState } from 'react';
import { Platform } from 'react-native';

export default function useVoiceRecognition() {
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  
  const { 
    setIsRecording, 
    setAudioLevel, 
    setIsProcessing,
    addMessage
  } = useChatStore();
  
  const { saveTranscripts } = useSettingsStore();

  // Request permissions
  useEffect(() => {
    (async () => {
      try {
        const { status } = await Audio.requestPermissionsAsync();
        if (status !== 'granted') {
          setError('Permission to access microphone is required!');
        }
      } catch (err) {
        setError('Error requesting microphone permission');
        console.error(err);
      }
    })();
  }, []);

  // Configure audio
  useEffect(() => {
    (async () => {
      try {
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
          staysActiveInBackground: false,
          shouldDuckAndroid: true,
        });
      } catch (err) {
        console.error('Failed to configure audio mode', err);
      }
    })();
  }, []);

  const startRecording = async () => {
    try {
      // Clear previous state
      setTranscript('');
      setError(null);
      
      // Provide haptic feedback
      if (Platform.OS !== 'web') {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      }
      
      // Create and prepare the recording
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      
      setRecording(recording);
      setIsRecording(true);
      
      // Set up recording status updates for visualization
      recording.setOnRecordingStatusUpdate((status) => {
        if (status.isRecording) {
          // metering is between -160 and 0, normalize to 0-1
          const level = status.metering ? (status.metering + 160) / 160 : 0;
          setAudioLevel(level);
        }
      });
      
      // Enable metering for visualization
      await recording.setProgressUpdateInterval(100);
      
    } catch (err) {
      console.error('Failed to start recording', err);
      setError('Failed to start recording');
    }
  };

  const stopRecording = async () => {
    if (!recording) return;
    
    try {
      // Provide haptic feedback
      if (Platform.OS !== 'web') {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      }
      
      setIsRecording(false);
      setAudioLevel(0);
      setIsProcessing(true);
      
      // Stop recording
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      
      if (!uri) {
        throw new Error('No recording URI available');
      }
      
      // In a real app, you would send the audio file to a speech-to-text service
      // For this demo, we'll simulate a response after a delay
      setTimeout(() => {
        const mockTranscript = "This is a simulated transcript. In a real app, this would be the result of speech-to-text conversion.";
        setTranscript(mockTranscript);
        
        // Add user message if transcripts should be saved
        if (saveTranscripts) {
          addMessage({
            id: Date.now().toString(),
            role: 'user',
            content: mockTranscript,
            timestamp: Date.now(),
          });
        }
        
        // Simulate API call to ChatGPT
        simulateChatGPTResponse(mockTranscript);
      }, 1500);
      
    } catch (err) {
      console.error('Failed to stop recording', err);
      setError('Failed to stop recording');
      setIsProcessing(false);
    }
  };

  const simulateChatGPTResponse = (userMessage: string) => {
    // In a real app, this would be an API call to ChatGPT
    setTimeout(() => {
      const responses = [
        "I've processed your voice input. How can I assist you further?",
        "I understand what you're saying. Is there anything specific you'd like to know?",
        "Thanks for the information. Would you like me to elaborate on any particular aspect?",
        "I've noted your message. Is there anything else you'd like to discuss?",
      ];
      
      const randomResponse = responses[Math.floor(Math.random() * responses.length)];
      
      if (saveTranscripts) {
        addMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content: randomResponse,
          timestamp: Date.now(),
        });
      }
      
      setIsProcessing(false);
    }, 2000);
  };

  const toggleRecording = async () => {
    if (recording) {
      await stopRecording();
    } else {
      await startRecording();
    }
  };

  return {
    isRecording: !!recording,
    transcript,
    error,
    toggleRecording,
  };
}