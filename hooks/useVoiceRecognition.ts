// Ajoutez cette ligne en haut de votre fichier si ce n'est pas déjà fait (pour TypeScript)
// /// <reference types="expo-av" /> 
// /// <reference types="expo-location" />
// /// <reference types="expo-file-system" />
// /// <reference types="expo-linking" />
// /// <reference types="expo-contacts" /> 

import { useChatStore } from '@/store/chat-store';
import { useSettingsStore } from '@/store/settings-store';
import axios from 'axios';
import { Audio, InterruptionModeAndroid, InterruptionModeIOS } from 'expo-av';
import * as Contacts from 'expo-contacts'; // NEW: Import Contacts
import * as FileSystem from 'expo-file-system';
import * as Linking from 'expo-linking';
import * as Location from 'expo-location';
import { useEffect, useRef, useState } from 'react';

const API_URL = 'https://alto-api-83dp.onrender.com/process-voice';

export default function useVoiceRecognition() {
  const recordingRef = useRef<Audio.Recording | null>(null);
  const [error, setError] = useState<string | null>(null);

  const {
    // isRecording: isRecordingFromStore, // Laissé tel quel, car vous utilisez recordingRef.current pour l'état isRecording retourné
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
           // NEW: Ajout d'un message utilisateur si permission refusée
          addMessage({ id: Date.now().toString(), role: 'assistant', content: "J'ai besoin de l'accès au microphone pour fonctionner.", timestamp: Date.now() });
        }
      } catch (err){ // NEW: Ajout de err pour le log
        console.error('Erreur demande permission micro:', err); // NEW: Log de l'erreur
        setError('Erreur permission micro');
        addMessage({ id: Date.now().toString(), role: 'assistant', content: "Un problème est survenu avec la permission du microphone.", timestamp: Date.now() });
      }
    })();
  }, [addMessage]); // NEW: Ajout de addMessage aux dépendances

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

// 📨 Fonction pour gérer l'envoi de SMS (version avec confirmation de contact)
const handleSendMessage = async (
  recipientName: string,
  messageContent: string
) => {
  try {
    // 1) Permissions
    const { status } = await Contacts.requestPermissionsAsync();
    if (status !== 'granted') {
      setError("Permission d'accès aux contacts refusée.");
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content:
          "Je ne peux pas envoyer de message sans l'accès à vos contacts. " +
          "Veuillez accorder la permission dans les réglages de votre téléphone.",
        timestamp: Date.now(),
      });
      return;
    }

    // 2) Recherche des contacts
    const { data: contactsFound } = await Contacts.getContactsAsync({
      name: recipientName,
      fields: [Contacts.Fields.PhoneNumbers],
    });

    if (!contactsFound || contactsFound.length === 0) {
      console.warn(`Aucun contact trouvé pour "${recipientName}"`);
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: `Je n'ai pas trouvé de contact nommé "${recipientName}". Pouvez-vous reformuler ou préciser le nom ?`,
        timestamp: Date.now(),
      });
      return;
    }

    // 3) Si plusieurs contacts, demander confirmation
    if (contactsFound.length > 1) {
      const namesList = contactsFound.map(c => c.name).join('", "');
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: `J'ai trouvé plusieurs contacts nommés "${recipientName}" : "${namesList}". Lequel voulez-vous ?`,
        timestamp: Date.now(),
      });
      return; // On attend la réponse de l'utilisateur
    }

    // 4) Un seul contact trouvé : on continue
    const contact = contactsFound[0];
    if (!contact.phoneNumbers || contact.phoneNumbers.length === 0) {
      console.warn(`Le contact "${contact.name}" n'a pas de numéro de téléphone.`);
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: `Le contact "${contact.name}" n'a pas de numéro de téléphone enregistré.`,
        timestamp: Date.now(),
      });
      return;
    }

    // 5) Extraction du numéro
    let phoneNumber =
      contact.phoneNumbers.find(p => p.label === 'mobile')?.number ||
      contact.phoneNumbers[0].number;
    if (!phoneNumber) {
      console.warn(`Impossible d'extraire un numéro pour "${contact.name}"`);
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: `Je n'ai pas pu récupérer de numéro pour "${contact.name}".`,
        timestamp: Date.now(),
      });
      return;
    }

    // 6) Construction et envoi du SMS
    const cleanedPhoneNumber = phoneNumber.replace(/\s+/g, '');
    const smsUrl = `sms:${cleanedPhoneNumber}?body=${encodeURIComponent(
      messageContent
    )}`;
    console.log('Ouverture de l\'URL SMS :', smsUrl);

    const supported = await Linking.canOpenURL(smsUrl);
    if (supported) {
      await Linking.openURL(smsUrl);
    } else {
      console.error('Impossible d\'ouvrir l\'application SMS via le lien.', smsUrl);
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content:
          "Je n'ai pas réussi à ouvrir votre application de messagerie. " +
          "Vérifiez qu'une application SMS soit configurée.",
        timestamp: Date.now(),
      });
    }
  } catch (e: any) {
    console.error("Erreur lors de la préparation de l'envoi du message:", e);
    addMessage({
      id: Date.now().toString(),
      role: 'assistant',
      content: `Erreur lors de la préparation du message : ${e.message || 'Inconnue'}.`,
      timestamp: Date.now(),
    });
  }
};



  const startRecording = async () => {
    // Votre logique startRecording d'origine
    setError(null); // NEW: Réinitialiser l'erreur au début
    try {
      const { granted } = await Audio.requestPermissionsAsync();
      if (!granted) {
          addMessage({ id: Date.now().toString(), role: 'assistant', content: "Je ne peux pas enregistrer sans la permission du microphone.", timestamp: Date.now() });
          return;
      }

      if (recordingRef.current) {
        try {
          await recordingRef.current.stopAndUnloadAsync();
        } catch (e) { console.warn("Ancien enregistrement: stopAndUnloadAsync a échoué", e) } // Logge l'erreur mais continue
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
        if (status.isRecording) { // Vérifier si status.isRecording est vrai
            const level = status.metering ? Math.max(0, (status.metering + 160) / 160) : 0;
            setAudioLevel(level);
        }
      });

      await recording.setProgressUpdateInterval(100);
      await recording.startAsync();

      recordingRef.current = recording;
      setIsRecording(true);
    } catch (err: any) { // NEW: Ajout de : any
      console.error('startRecording error:', err);
      setError(`Erreur démarrage: ${err.message || 'Inconnue'}`);
    }
  };

  const stopRecording = async () => {
    let mp3FilePathToDelete: string | null = null;
  
    try {
      const recording = recordingRef.current;
      if (!recording) return;
  
      // Stop & unload recording
      await recording.stopAndUnloadAsync();
      setIsRecording(false);
      setAudioLevel(0);
      setIsProcessing(true);
  
      const uri = recording.getURI();
      recordingRef.current = null;
      if (!uri) {
        setIsProcessing(false);
        return;
      }
  
      // Permissions localisation
      const { status } = await Location.requestForegroundPermissionsAsync();
      let latitude: number | null = null;
      let longitude: number | null = null;
      if (status === 'granted') {
        const loc = await Location.getCurrentPositionAsync({});
        latitude = loc.coords.latitude;
        longitude = loc.coords.longitude;
      } else {
        setError('Permission localisation refusée');
        addMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content:
            "Sans accès à votre position, certaines fonctionnalités comme les itinéraires pourraient ne pas fonctionner.",
          timestamp: Date.now(),
        });
      }
  
      // Préparation FormData
      const formData = new FormData();
      const fileType = uri.endsWith('.wav') ? 'audio/wav' : 'audio/webm';
      formData.append('file', {
        uri,
        name: `audio.${uri.split('.').pop() || 'webm'}`,
        type: fileType,
      } as any);
      if (latitude !== null && longitude !== null) {
        formData.append('lat', latitude.toString());
        formData.append('lng', longitude.toString());
      }
  
      // Envoi au backend
      const response = await axios.post(API_URL, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const { transcript, response_text, audio: base64Audio, action } = response.data;
      const assistantTextToUse = response_text || '[Réponse vide]';
  
      // Vérification contact avant SMS
      let finalText = assistantTextToUse;
      let finalAction = action;
      if (action?.type === 'send_message') {
        const { data: contactsFound } = await Contacts.getContactsAsync({
          name: action.data.recipient_name,
          fields: [Contacts.Fields.PhoneNumbers],
        });
        if (!contactsFound || contactsFound.length === 0) {
          finalText = `Je n'ai pas trouvé de contact nommé "${action.data.recipient_name}".`;
          finalAction = null;
          addMessage({
            id: Date.now().toString(),
            role: 'assistant',
            content: finalText,
            timestamp: Date.now(),
          });
        }
      }
  
      // Écriture du MP3 TTS
      const mp3Path = FileSystem.documentDirectory + 'response.mp3';
      mp3FilePathToDelete = mp3Path;
      await FileSystem.writeAsStringAsync(mp3Path, base64Audio, {
        encoding: FileSystem.EncodingType.Base64,
      });
  
      // Forcer haut-parleur
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
        interruptionModeIOS: InterruptionModeIOS.DuckOthers,
        staysActiveInBackground: false,
        interruptionModeAndroid: InterruptionModeAndroid.DuckOthers,
        shouldDuckAndroid: false,
        playThroughEarpieceAndroid: false,
      });
  
      // Lecture du TTS
      const sound = new Audio.Sound();
      let soundPlayedSuccessfully = false;
      try {
        await sound.loadAsync({ uri: mp3Path });
        await sound.playAsync();
        soundPlayedSuccessfully = true;
      } catch (playError) {
        console.error('Erreur lecture TTS:', playError);
        addMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content: "Désolé, je n'ai pas pu lire ma réponse vocale.",
          timestamp: Date.now(),
        });
        // Si action maps
        if (action?.type === 'maps' && action.data.maps_url) {
          Linking.openURL(action.data.maps_url).catch(console.error);
        }
        setIsProcessing(false);
        return;
      }
  
      // Sauvegarde des transcripts
      if (saveTranscripts) {
        const now = Date.now();
        addMessage({
          id: now.toString(),
          role: 'user',
          content: transcript?.trim() || '[Message audio]',
          timestamp: now,
        });
        addMessage({
          id: (now + 1).toString(),
          role: 'assistant',
          content: finalText.trim(),
          timestamp: now + 1,
        });
      }
  
      // Callback fin de lecture
      sound.setOnPlaybackStatusUpdate(async (status) => {
        if (!status.isLoaded) return;
        if (status.didJustFinish && !status.isLooping) {
          await sound.unloadAsync().catch(console.warn);
  
          if (finalAction?.type === 'maps') {
            await Linking.openURL(finalAction.data.maps_url).catch(console.error);
          } else if (finalAction?.type === 'send_message') {
            await handleSendMessage(
              finalAction.data.recipient_name,
              finalAction.data.message_content
            );
          }
          setIsProcessing(false);
        }
      });
    } catch (err: any) {
      console.error('stopRecording error:', err);
      setError(`Erreur traitement vocal: ${err.message || 'Inconnue'}`);
      setIsProcessing(false);
    } finally {
      if (mp3FilePathToDelete) {
        FileSystem.deleteAsync(mp3FilePathToDelete, { idempotent: true }).catch(
          console.warn
        );
      }
    }
  };
  
  
  
  const toggleRecording = async () => {
    // Votre logique toggleRecording d'origine
    if (recordingRef.current) {
      await stopRecording();
    } else {
      await startRecording();
    }
  };

  return {
    isRecording: !!recordingRef.current, // Votre logique d'origine pour isRecording
    error,
    toggleRecording,
  };
}