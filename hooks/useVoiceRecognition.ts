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
const TTS_ONLY_URL = 'https://alto-api-83dp.onrender.com/tts-only';

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
    // La vérification de permission contact est déjà faite avant d'appeler handleSendMessage
    // si l'action vient de stopRecording. Mais on la garde ici pour un usage direct potentiel.
    const { status } = await Contacts.requestPermissionsAsync();
    if (status !== 'granted') {
      setError("Permission d'accès aux contacts refusée.");
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: "Je ne peux pas envoyer de message sans l'accès à vos contacts. Veuillez accorder la permission dans les réglages de votre téléphone.",
        timestamp: Date.now(),
      });
      return;
    }

    const { data: contactsFound } = await Contacts.getContactsAsync({
      name: recipientName,
      fields: [Contacts.Fields.PhoneNumbers],
    });

    if (!contactsFound || contactsFound.length === 0) {
      // Ce cas devrait être intercepté plus tôt dans stopRecording,
      // mais on le garde comme double sécurité ou si handleSendMessage est appelé autrement.
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: `Je n'ai pas trouvé de contact nommé "${recipientName}".`,
        timestamp: Date.now(),
      });
      return;
    }

    if (contactsFound.length > 1) {
      const namesList = contactsFound.map(c => c.name).join('", "');
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: `J'ai trouvé plusieurs contacts nommés "${recipientName}" : "${namesList}". Lequel voulez-vous ?`,
        timestamp: Date.now(),
      });
      return;
    }

    const contact = contactsFound[0];
    if (!contact.phoneNumbers?.length) {
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: `Le contact "${contact.name}" n'a pas de numéro de téléphone enregistré.`,
        timestamp: Date.now(),
      });
      return;
    }

    let phoneNumber = contact.phoneNumbers.find(p => p.label === 'mobile')?.number
      || contact.phoneNumbers[0].number;
    if (!phoneNumber) {
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: `Je n'ai pas pu récupérer de numéro pour "${contact.name}".`,
        timestamp: Date.now(),
      });
      return;
    }

    const cleaned = phoneNumber.replace(/\s+/g, '');
    const smsUrl = `sms:${cleaned}?body=${encodeURIComponent(messageContent)}`;
    const supported = await Linking.canOpenURL(smsUrl);
    if (supported) {
      await Linking.openURL(smsUrl);
      // Optionnel : ajouter un message de confirmation que l'app SMS a été ouverte
      // addMessage({ role: 'assistant', content: 'Ouverture de votre application SMS...' });
    } else {
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: "Je n'ai pas réussi à ouvrir votre application de messagerie. Vérifiez qu'une application SMS soit configurée.",
        timestamp: Date.now(),
      });
    }
  } catch (e: any) {
    console.error('Erreur préparation envoi SMS:', e);
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
      /* 1) STOP & UNLOAD ---------------------------------------------------- */
      const recording = recordingRef.current;
      if (!recording) return;
      await recording.stopAndUnloadAsync();
      setIsRecording(false);
      setAudioLevel(0);
      setIsProcessing(true);
  
      /* 2) RÉCUPÈRE L’URI --------------------------------------------------- */
      const uri = recording.getURI();
      recordingRef.current = null;
      if (!uri) { setIsProcessing(false); return; }
  
      /* 3) LOCALISATION ----------------------------------------------------- */
      const { status: locStatus } = await Location.requestForegroundPermissionsAsync();
      let latitude: number | null = null;
      let longitude: number | null = null;
      if (locStatus === 'granted') {
        const loc = await Location.getCurrentPositionAsync({});
        latitude = loc.coords.latitude;
        longitude = loc.coords.longitude;
      } else {
        setError('Permission localisation refusée');
        addMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content: "Sans accès à votre position, certaines fonctionnalités comme les itinéraires pourraient ne pas fonctionner.",
          timestamp: Date.now(),
        });
      }
  
      /* 4) ENVOI AU BACKEND ------------------------------------------------- */
      const formData = new FormData();
      const fileType = uri.endsWith('.wav') ? 'audio/wav' : 'audio/webm';
      formData.append('file', { uri, name: `audio.${uri.split('.').pop()}`, type: fileType } as any);
      if (latitude !== null && longitude !== null) {
        formData.append('lat', latitude.toString());
        formData.append('lng', longitude.toString());
      }
  
      const { data } = await axios.post(API_URL, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const { transcript, response_text, audio: backendAudio64, action } = data;
      const backendText = response_text || '[Réponse vide]';
  
      /* 5) CONTACT & PERMISSION CHECK AVANT TTS ----------------------------- */
      let finalText   = backendText;
      let finalAction = action;
      let audioBase64 = backendAudio64;   // sera remplacé si finalText change
  
      const regenerateTTS = async () => {
        try {
          const ttsResp = await axios.post(
            TTS_ONLY_URL,
            new URLSearchParams({ text: finalText }).toString(),
            { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
          );
          audioBase64 = ttsResp.data.audio || '';
        } catch (e) {
          console.error('Échec du TTS alternatif :', e);
          audioBase64 = '';
        }
      };
  
      if (action?.type === 'send_message') {
        /* 5a) Permission contacts */
        const { status: perm } = await Contacts.requestPermissionsAsync();
        if (perm !== 'granted') {
          finalText   = "Je ne peux pas envoyer de message sans l'accès à vos contacts. Veuillez accorder la permission.";
          finalAction = null;
          await regenerateTTS();
        } else {
          /* 5b) Existence / ambiguïté du contact */
          const { data: contactsFound } = await Contacts.getContactsAsync({
            name: action.data.recipient_name,
            fields: [Contacts.Fields.PhoneNumbers],
          });
  
          if (contactsFound.length > 1) {
            // Plusieurs homonymes → on demande lequel
            const names = contactsFound.map(c => c.name).join('", "');
            finalText   = `J'ai trouvé plusieurs contacts nommés "${action.data.recipient_name}" : "${names}". Lequel voulez-vous ?`;
            finalAction = null;   // on bloque l’envoi tant que l’utilisateur n’a pas choisi
            await regenerateTTS();
          } else if (contactsFound.length === 0) {
            // Aucun contact
            finalText   = `Je n'ai pas trouvé de contact nommé "${action.data.recipient_name}".`;
            finalAction = null;
            await regenerateTTS();
          }
        }
      }
  
      /* 6) LECTURE DU TTS --------------------------------------------------- */
      const sound     = new Audio.Sound();
      let soundLoaded = false;
      if (audioBase64) {
        const mp3Path = FileSystem.documentDirectory + 'response.mp3';
        mp3FilePathToDelete = mp3Path;
        await FileSystem.writeAsStringAsync(mp3Path, audioBase64, {
          encoding: FileSystem.EncodingType.Base64,
        });
  
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: false,
          playsInSilentModeIOS: true,
          interruptionModeIOS: InterruptionModeIOS.DuckOthers,
          staysActiveInBackground: false,
          interruptionModeAndroid: InterruptionModeAndroid.DuckOthers,
          shouldDuckAndroid: false,
          playThroughEarpieceAndroid: false,
        });
  
        try {
          await sound.loadAsync({ uri: mp3Path });
          await sound.playAsync();
          soundLoaded = true;
        } catch (e) {
          console.error('Erreur lecture TTS :', e);
          addMessage({
            id: Date.now().toString(),
            role: 'assistant',
            content: "Désolé, je n'ai pas pu lire ma réponse vocale.",
            timestamp: Date.now(),
          });
        }
      } else {
        console.warn('Aucun MP3 disponible ; la réponse sera affichée sans voix.');
      }
  
      /* 7) HISTORIQUE CHAT -------------------------------------------------- */
      if (saveTranscripts) {
        const now = Date.now();
        addMessage({ id: now.toString(),       role: 'user',      content: transcript?.trim() || '[Message audio]', timestamp: now });
        addMessage({ id: (now + 1).toString(), role: 'assistant', content: finalText.trim(),                       timestamp: now + 1 });
      }
  
      /* 8) ACTION APRÈS LE TTS --------------------------------------------- */
      const doAction = async () => {
        if (finalAction?.type === 'maps') {
          await Linking.openURL(finalAction.data.maps_url).catch(console.error);
        } else if (finalAction?.type === 'send_message') {
          await handleSendMessage(finalAction.data.recipient_name, finalAction.data.message_content);
        }
        setIsProcessing(false);
      };
  
      /* 9) FIN DE LECTURE OU PAS DE SON ------------------------------------ */
      if (soundLoaded) {
        sound.setOnPlaybackStatusUpdate(async status => {
          if ('isLoaded' in status && status.isLoaded && status.didJustFinish && !status.isLooping) {
            await sound.unloadAsync().catch(console.warn);
            await doAction();
          }
        });
      } else {
        await doAction();
      }
  
    } catch (err: any) {
      console.error('stopRecording error:', err);
      setError(`Erreur traitement vocal: ${err.message || 'Inconnue'}`);
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: `Une erreur est survenue: ${err.message || 'Inconnue'}.`,
        timestamp: Date.now(),
      });
      setIsProcessing(false);
    } finally {
      if (mp3FilePathToDelete) {
        FileSystem.deleteAsync(mp3FilePathToDelete, { idempotent: true }).catch(console.warn);
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