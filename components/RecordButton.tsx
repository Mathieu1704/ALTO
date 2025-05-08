import React, { useRef } from 'react';
import { TouchableOpacity, StyleSheet, View, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Colors from '@/constants/colors';
import { useChatStore } from '@/store/chat-store';
import { useSettingsStore } from '@/store/settings-store';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import axios from 'axios';

const API_URL = 'https://alto-api-zlw8.onrender.com/process-voice';

export default function RecordButton() {
  const { isRecording, setIsRecording } = useChatStore();
  const { isDarkTheme } = useSettingsStore();
  const theme = isDarkTheme ? Colors.dark : Colors.light;

  const recordingRef = useRef<Audio.Recording | null>(null);

  const toggleRecording = async () => {
    Alert.alert("🧪", "Le bouton a été cliqué");
    try {
      if (!isRecording) {
        Alert.alert("🎙️", "Démarrage de l'enregistrement...");
        const { granted } = await Audio.requestPermissionsAsync();

        if (!granted) {
          Alert.alert('Micro refusé', 'Permission requise pour enregistrer.');
          return;
        }

        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
          staysActiveInBackground: false,
        });

        recordingRef.current = new Audio.Recording();
        const recording = recordingRef.current;

        const recordingOptions = {
          android: {
            extension: '.wav',
            outputFormat: 1,
            audioEncoder: 1,
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
        };

        await recording.prepareToRecordAsync(recordingOptions);
        await recording.startAsync();
        setIsRecording(true);
        Alert.alert("✅", "Enregistrement démarré");

      } else {
        const recording = recordingRef.current;
        if (!recording) {
          Alert.alert("⚠️", "Impossible d'arrêter : référence manquante.");
          return;
        }

        await recording.stopAndUnloadAsync();
        setIsRecording(false);
        Alert.alert("🛑", "Enregistrement terminé");

        const uri = recording.getURI();
        if (!uri) {
          Alert.alert("⚠️", "Fichier audio introuvable.");
          return;
        }

        Alert.alert("📤", "Envoi à l'API...");
        const formData = new FormData();
        formData.append('file', {
          uri,
          name: 'audio.wav',
          type: 'audio/wav',
        } as any);

        const response = await axios.post(API_URL, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          responseType: 'arraybuffer',
        });

        Alert.alert("✅", "Réponse reçue. Lecture en cours...");

        const mp3Path = FileSystem.documentDirectory + 'response.mp3';
        await FileSystem.writeAsStringAsync(
          mp3Path,
          Buffer.from(response.data).toString('base64'),
          { encoding: FileSystem.EncodingType.Base64 }
        );

        const sound = new Audio.Sound();
        await sound.loadAsync({ uri: mp3Path });
        await sound.playAsync();
      }
    } catch (error) {
      setIsRecording(false);
      Alert.alert('❌ Erreur', 'Une erreur est survenue : ' + (error as Error).message);
    }
  };

  return (
    <TouchableOpacity
      style={[
        styles.button,
        { backgroundColor: isRecording ? theme.accent : theme.primary }
      ]}
      onPress={toggleRecording}
      activeOpacity={0.7}
    >
      <View style={styles.iconContainer}>
        {isRecording ? (
          <Ionicons name="stop" size={24} color="#FFFFFF" />
        ) : (
          <Ionicons name="mic" size={24} color="#FFFFFF" />
        )}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    width: 64,
    height: 64,
    borderRadius: 32,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 5,
  },
  iconContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
