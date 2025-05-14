import { useChatStore } from '@/store/chat-store';
import { useSettingsStore } from '@/store/settings-store';
import axios from 'axios';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import * as Linking from 'expo-linking';
import * as Location from 'expo-location';
import { useEffect, useRef, useState } from 'react';

const API_URL = 'https://alto-api-83dp.onrender.com/process-voice';

export default function useVoiceRecognition() {
  const recordingRef = useRef<Audio.Recording | null>(null);
  const [error, setError] = useState<string | null>(null);

  const {
    setIsRecording,
    setAudioLevel,
    setIsProcessing,
    addMessage,
  } = useChatStore();
  const { saveTranscripts } = useSettingsStore();

  useEffect(() => {
    (async () => {
      try {
        const { status } = await Audio.requestPermissionsAsync();
        if (status !== 'granted') {
          setError('Permission micro refusée');
        }
      } catch {
        setError('Erreur permission micro');
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      try {
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
          staysActiveInBackground: false,
          shouldDuckAndroid: true,
          playThroughEarpieceAndroid: false,
        });
      } catch (err) {
        console.error('Audio mode error', err);
      }
    })();
  }, []);

  const startRecording = async () => {
    try {
      const { granted } = await Audio.requestPermissionsAsync();
      if (!granted) return;

      if (recordingRef.current) {
        try {
          await recordingRef.current.stopAndUnloadAsync();
        } catch {}
        recordingRef.current = null;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: false,
      });

      const recording = new Audio.Recording();
      await recording.prepareToRecordAsync({
        android: {
          extension: '.webm',
          outputFormat: 2,
          audioEncoder: 2,
          sampleRate: 44100,
          numberOfChannels: 1,
          bitRate: 128000,
        },
        ios: {
          extension: '.wav',
          audioQuality: 0,
          sampleRate: 44100,
          numberOfChannels: 1,
          bitRate: 128000,
          linearPCMBitDepth: 16,
          linearPCMIsBigEndian: false,
          linearPCMIsFloat: false,
        },
        web: {
          mimeType: 'audio/webm',
          bitsPerSecond: 128000,
        },
        isMeteringEnabled: true,
      });

      recording.setOnRecordingStatusUpdate((status) => {
        const level = status.metering ? (status.metering + 160) / 160 : 0;
        setAudioLevel(level);
      });

      await recording.setProgressUpdateInterval(100);
      await recording.startAsync();

      recordingRef.current = recording;
      setIsRecording(true);
    } catch (err) {
      console.error('startRecording error:', err);
      setError('Erreur démarrage');
    }
  };

  const stopRecording = async () => {
    try {
      const recording = recordingRef.current;
      if (!recording) return;

      await recording.stopAndUnloadAsync();
      setIsRecording(false);
      setAudioLevel(0);
      setIsProcessing(true);

      const uri = recording.getURI();
      recordingRef.current = null;
      if (!uri) return;

      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setError('Permission localisation refusée');
        setIsProcessing(false);
        return;
      }

      const location = await Location.getCurrentPositionAsync({});
      const { latitude, longitude } = location.coords;

      const formData = new FormData();
      formData.append('file', {
        uri,
        name: 'audio.webm',
        type: 'audio/webm',
      } as any);
      formData.append('lat', latitude.toString());
      formData.append('lng', longitude.toString());

      const response = await axios.post(API_URL, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const { transcript, response: assistantText, audio: base64Audio, maps_url } = response.data;

      const mp3Path = FileSystem.documentDirectory + 'response.mp3';
      await FileSystem.writeAsStringAsync(mp3Path, base64Audio, {
        encoding: FileSystem.EncodingType.Base64,
      });

      const sound = new Audio.Sound();
      await sound.loadAsync({ uri: mp3Path });
      await sound.playAsync();

      if (saveTranscripts) {
        const now = Date.now();
        addMessage({ id: now.toString(), role: 'user', content: transcript?.trim() || '[Message audio]', timestamp: now });
        addMessage({ id: (now + 1).toString(), role: 'assistant', content: assistantText?.trim() || '[Réponse vide]', timestamp: now + 1 });
      }

      if (maps_url) {
        console.log("maps_url reçu :", maps_url);

        sound.setOnPlaybackStatusUpdate((status) => {
          if (!status.isLoaded) return;
        
          if (status.didJustFinish && !status.isLooping) {
            Linking.canOpenURL(maps_url).then((supported) => {
              if (supported) {
                Linking.openURL(maps_url);
              } else {
                console.error("Impossible d'ouvrir l'URL :", maps_url);
              }
            });
          }
        });
      }

      setIsProcessing(false);
    } catch (err) {
      console.error('stopRecording error:', err);
      setError('Erreur traitement vocal');
      setIsProcessing(false);
    }
  };

  const toggleRecording = async () => {
    if (recordingRef.current) {
      await stopRecording();
    } else {
      await startRecording();
    }
  };

  return {
    isRecording: !!recordingRef.current,
    error,
    toggleRecording,
  };
}
