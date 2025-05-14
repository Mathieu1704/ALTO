import { useState, useEffect, useRef } from 'react';
import { Platform } // NOUVEAU: Pour potentiellement différencier les schémas d'URL SMS
from 'react-native';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import * as Location from 'expo-location';
import * as Linking from 'expo-linking';
import * as Contacts from 'expo-contacts'; // NOUVEAU: Pour accéder aux contacts
import axios from 'axios';
import { useChatStore } from '@/store/chat-store';
import { useSettingsStore } from '@/store/settings-store';

// Assure-toi que cette URL est correcte et accessible
const API_URL = 'https://alto-api-zlw8.onrender.com/process-voice';
// Pour la démo, si tu testes en local avec un backend local:
// import { Platform } from 'react-native';
// const API_URL = Platform.OS === 'android' ? 'http://10.0.2.2:8000/process-voice' : 'http://localhost:8000/process-voice';


export default function useVoiceRecognition() {
  const recordingRef = useRef<Audio.Recording | null>(null);
  const [error, setError] = useState<string | null>(null);
  const soundRef = useRef<Audio.Sound | null>(null); // NOUVEAU: Pour gérer le déchargement du son

  const {
    isRecording, // NOUVEAU: Lire directement l'état depuis le store
    setIsRecording,
    setAudioLevel,
    setIsProcessing,
    addMessage,
  } = useChatStore();
  const { saveTranscripts } = useSettingsStore();

  // Demande de permission Micro au montage
  useEffect(() => {
    (async () => {
      try {
        const { status } = await Audio.requestPermissionsAsync();
        if (status !== 'granted') {
          setError('Permission micro refusée. Veuillez l\'activer dans les paramètres de l\'application.');
        }
      } catch (err) {
        console.error("Erreur de permission micro:", err);
        setError('Erreur lors de la demande de permission micro.');
      }
    })();
  }, []);

  // Configuration du mode audio
  useEffect(() => {
    (async () => {
      try {
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true, // Important pour que le son joue même en mode silencieux
          staysActiveInBackground: false, // À évaluer selon les besoins si l'app doit continuer en arrière-plan
          shouldDuckAndroid: true,    // Baisse le volume des autres apps pendant l'enregistrement/lecture
          playThroughEarpieceAndroid: false, // Joue par le haut-parleur principal
        });
      } catch (err) {
        console.error('Erreur de configuration du mode Audio:', err);
      }
    })();

    // Nettoyage du son au démontage du composant
    return () => {
      soundRef.current?.unloadAsync();
    };
  }, []);

  // NOUVEAU: Fonction pour gérer l'intention d'envoyer un message
  const handleSendMessageIntent = async (recipientQuery: string, messageContent: string) => {
    console.log(`Intention d'envoyer un message détectée: À: ${recipientQuery}, Message: ${messageContent}`);
    setIsProcessing(true); // Indiquer que l'on traite quelque chose

    try {
      const { status } = await Contacts.requestPermissionsAsync();
      if (status !== 'granted') {
        setError("Permission d'accès aux contacts refusée.");
        addMessage({
            id: Date.now().toString(),
            role: 'assistant',
            content: "Je ne peux pas accéder à vos contacts sans votre permission.",
            timestamp: Date.now(),
        });
        setIsProcessing(false);
        return;
      }

      const { data: contactsFound } = await Contacts.getContactsAsync({
        name: recipientQuery,
        fields: [Contacts.Fields.PhoneNumbers, Contacts.Fields.Name],
      });

      if (!contactsFound || contactsFound.length === 0) {
        console.log(`Aucun contact trouvé pour "${recipientQuery}"`);
        addMessage({
            id: Date.now().toString(),
            role: 'assistant',
            content: `Je n'ai trouvé aucun contact correspondant à "${recipientQuery}".`,
            timestamp: Date.now(),
        });
        // Optionnel: TTS pour ce message d'erreur (nécessiterait un appel API /tts-only)
        setIsProcessing(false);
        return;
      }

      let targetContact = contactsFound[0]; // Simplification: prendre le premier contact trouvé

      if (contactsFound.length > 1) {
        console.warn(`Plusieurs contacts trouvés pour "${recipientQuery}". Pris le premier: ${targetContact.name}`);
        // Pour une V2: demander à l'utilisateur de préciser via une réponse vocale ou une UI.
        // Par exemple, Alto pourrait dire : "J'ai trouvé plusieurs contacts pour [recipientQuery] : [Nom1], [Nom2]. Lequel choisissez-vous ?"
        // Cela nécessiterait une nouvelle interaction avec l'API backend.
         addMessage({
            id: Date.now().toString(),
            role: 'assistant',
            content: `J'ai trouvé plusieurs contacts pour "${recipientQuery}". J'ai choisi ${targetContact.name}. Pour envoyer au bon contact, essayez d'être plus précis, par exemple en donnant le nom et prénom.`,
            timestamp: Date.now(),
        });
      }

      if (!targetContact.phoneNumbers || targetContact.phoneNumbers.length === 0) {
        console.log(`Le contact "${targetContact.name}" n'a pas de numéro de téléphone.`);
         addMessage({
            id: Date.now().toString(),
            role: 'assistant',
            content: `Le contact "${targetContact.name}" n'a pas de numéro de téléphone enregistré.`,
            timestamp: Date.now(),
        });
        setIsProcessing(false);
        return;
      }

      const phoneNumber = targetContact.phoneNumbers[0].number; // Simplification: prendre le premier numéro
      console.log(`Numéro trouvé pour ${targetContact.name}: ${phoneNumber}`);

      const encodedMessage = encodeURIComponent(messageContent);
      let smsUrl = `sms:${phoneNumber}`;

      if (Platform.OS === 'android') {
        smsUrl += `?body=${encodedMessage}`;
      } else if (Platform.OS === 'ios') {
        smsUrl += `&body=${encodedMessage}`; // Pour iOS, le séparateur est &
      }
      // Pour WhatsApp:
      // const whatsappPhoneNumber = phoneNumber.replace(/[^0-9+]/g, ''); // Nettoyer et garder le + pour code pays
      // const whatsappUrl = `whatsapp://send?phone=${whatsappPhoneNumber}&text=${encodedMessage}`;

      const supported = await Linking.canOpenURL(smsUrl);
      if (supported) {
        addMessage({
            id: Date.now().toString(),
            role: 'assistant',
            content: `Ok, j'ouvre l'application de messages pour envoyer à ${targetContact.name}.`,
            timestamp: Date.now(),
        });
        await Linking.openURL(smsUrl);
      } else {
        console.error(`Impossible d'ouvrir l'URL SMS: ${smsUrl}`);
        setError(`Impossible d'ouvrir l'application de messagerie.`);
        addMessage({
            id: Date.now().toString(),
            role: 'assistant',
            content: "Je n'ai pas pu ouvrir votre application de messagerie.",
            timestamp: Date.now(),
        });
      }
    } catch (e: any) {
      console.error("Erreur lors de la gestion de l'envoi de message:", e);
      setError(`Erreur envoi message: ${e.message}`);
      addMessage({
            id: Date.now().toString(),
            role: 'assistant',
            content: "Une erreur est survenue lors de la préparation du message.",
            timestamp: Date.now(),
        });
    } finally {
      setIsProcessing(false);
    }
  };


  const startRecording = async () => {
    setError(null); // Réinitialiser les erreurs
    try {
      // Vérifier à nouveau la permission micro, au cas où elle aurait été révoquée
      const { granted } = await Audio.requestPermissionsAsync();
      if (!granted) {
        setError('Permission micro requise pour enregistrer.');
        return;
      }

      // S'assurer qu'un enregistrement précédent est bien arrêté et déchargé
      if (recordingRef.current) {
        console.log("Nettoyage d'un enregistrement précédent.");
        try {
          await recordingRef.current.stopAndUnloadAsync();
        } catch (unloadError) {
          // Ignorer les erreurs ici, car on va créer un nouvel enregistrement
          console.warn("Erreur mineure au déchargement de l'ancien enregistrement:", unloadError);
        }
        recordingRef.current = null;
      }
      
      // Décharger un son précédent s'il existe
      if (soundRef.current) {
        await soundRef.current.unloadAsync();
        soundRef.current = null;
      }


      // La configuration du mode audio est déjà faite dans useEffect, pas besoin de la répéter ici
      // sauf si des paramètres spécifiques sont nécessaires juste avant l'enregistrement.

      const recording = new Audio.Recording();
      recordingRef.current = recording; // Assigner avant prepareToRecordAsync

      await recording.prepareToRecordAsync(
        Platform.OS === 'ios' 
        ? Audio.RecordingOptionsPresets.HIGH_QUALITY // .wav par défaut sur iOS avec HIGH_QUALITY et metering activé
        : { 
            android: {
              extension: '.m4a', // L'extension que tu souhaites pour le fichier
              outputFormat: Audio.AndroidOutputFormat.MPEG_4, // Correction ici
              audioEncoder: Audio.AndroidAudioEncoder.AAC,    // Correction ici
              sampleRate: 44100,
              numberOfChannels: 1,
              bitRate: 128000,
              // isMeteringEnabled est une option de haut niveau, pas spécifique à android ici
            },
            ios: Audio.RecordingOptionsPresets.HIGH_QUALITY.ios, 
            web: Audio.RecordingOptionsPresets.HIGH_QUALITY.web, 
            isMeteringEnabled: true, // Placer isMeteringEnabled au niveau supérieur des options
          }
      );

      recording.setOnRecordingStatusUpdate((status) => {
        if (status.isRecording) {
          const level = status.metering ? Math.max(0, (status.metering + 160) / 160) : 0; // Normaliser et clamper
          setAudioLevel(level);
        }
      });
      await recording.setProgressUpdateInterval(100);
      await recording.startAsync();
      setIsRecording(true);

    } catch (err: any) {
      console.error('Erreur au démarrage de l\'enregistrement:', err);
      setError(`Erreur démarrage enregistrement: ${err.message}`);
      setIsRecording(false); // S'assurer que l'état est correct
      if (recordingRef.current) { // Tenter de nettoyer si l'objet existe
          try { await recordingRef.current.stopAndUnloadAsync(); } catch {}
          recordingRef.current = null;
      }
    }
  };

  const stopRecording = async () => {
    if (!recordingRef.current) {
      console.log("Aucun enregistrement en cours à arrêter.");
      return;
    }
    
    setIsProcessing(true); // Indiquer qu'on traite, avant même l'arrêt effectif
    setIsRecording(false); // Mettre à jour l'état immédiatement
    setAudioLevel(0);

    try {
      const recording = recordingRef.current;
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      recordingRef.current = null; // Important de le mettre à null APRÈS getURI

      if (!uri) {
        setError('Impossible d\'obtenir l\'URI de l\'enregistrement.');
        setIsProcessing(false);
        return;
      }

      // Demande de permission de localisation
      const { status: locStatus } = await Location.requestForegroundPermissionsAsync();
      let latitude: number | null = null;
      let longitude: number | null = null;

      if (locStatus === 'granted') {
        const location = await Location.getCurrentPositionAsync({});
        latitude = location.coords.latitude;
        longitude = location.coords.longitude;
      } else {
        console.warn('Permission de localisation refusée ou non disponible.');
        // Pas besoin de bloquer, le backend gère lat/lng comme optionnels
        // On pourrait afficher un message à l'utilisateur si la localisation est critique.
        // addMessage({ id: Date.now().toString(), role: 'assistant', content: "Je n'ai pas accès à votre localisation. Certaines fonctionnalités comme les itinéraires pourraient ne pas fonctionner.", timestamp: Date.now() });
      }

      const formData = new FormData();
      const filename = Platform.OS === 'ios' ? 'audio.wav' : 'audio.m4a'; // Adapter le nom de fichier et type
      const mimeType = Platform.OS === 'ios' ? 'audio/wav' : 'audio/m4a'; // Adapter le nom de fichier et type

      formData.append('file', {
        uri,
        name: filename, 
        type: mimeType,
      } as any);

      // N'ajouter lat/lng que s'ils sont disponibles
      if (latitude !== null) formData.append('lat', latitude.toString());
      if (longitude !== null) formData.append('lng', longitude.toString());

      console.log("Envoi des données au serveur...");
      const response = await axios.post(API_URL, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000, // Timeout de 30 secondes pour l'appel API
      });

      // MODIFIÉ: Adapter aux nouvelles clés de réponse du backend
      const {
        transcript,
        response_text: assistantText,
        audio_base64: base64Audio,
        action_data // Nouvelle clé pour les actions
      } = response.data;

      console.log("Réponse du serveur reçue. Transcript:", transcript);
      console.log("Texte de l'assistant:", assistantText);
      if(action_data) console.log("Action Data:", JSON.stringify(action_data));


      // Sauvegarder les messages dans le store (si l'option est activée)
      if (saveTranscripts) {
        const now = Date.now();
        if (transcript?.trim()) {
            addMessage({ id: now.toString(), role: 'user', content: transcript.trim(), timestamp: now });
        }
        // Ajouter la réponse de l'assistant même si elle est vide, pour le contexte, ou gérer autrement
        addMessage({ id: (now + 1).toString(), role: 'assistant', content: assistantText?.trim() || (action_data ? "[Action en cours...]" : "[Pas de réponse textuelle]"), timestamp: now + 1 });
      }

      let soundPlaybackFinished = false; // Flag pour gérer la fin de la lecture audio

      // Fonction pour exécuter l'action après la fin du TTS
      const executePostTTSAction = async () => {
        if (soundPlaybackFinished) return; // Éviter exécution multiple
        soundPlaybackFinished = true;

        if (action_data) {
            if (action_data.type === 'OPEN_MAPS' && action_data.payload?.url) {
                console.log("Ouverture de Google Maps avec URL:", action_data.payload.url);
                const supported = await Linking.canOpenURL(action_data.payload.url);
                if (supported) {
                    await Linking.openURL(action_data.payload.url);
                } else {
                    console.error("Impossible d'ouvrir l'URL Maps:", action_data.payload.url);
                    setError(`Impossible d'ouvrir l'URL: ${action_data.payload.url}`);
                }
            } else if (action_data.type === 'PREPARE_SEND_MESSAGE' && action_data.payload) {
                await handleSendMessageIntent(action_data.payload.recipient_query, action_data.payload.message_content);
            }
            // Ajouter d'autres types d'actions ici si besoin
        }
        setIsProcessing(false); // Fin du traitement global
      };


      // Jouer l'audio de la réponse de l'assistant
      if (base64Audio) {
        const mp3Path = FileSystem.documentDirectory + 'response.mp3'; // Nommer en .mp3 car c'est ce que le backend envoie
        await FileSystem.writeAsStringAsync(mp3Path, base64Audio, {
          encoding: FileSystem.EncodingType.Base64,
        });

        const sound = new Audio.Sound();
        soundRef.current = sound; // Stocker la référence
        
        sound.setOnPlaybackStatusUpdate(async (status) => {
          if (!status.isLoaded) {
            if (status.error) {
              console.error(`Erreur de lecture audio: ${status.error}`);
              setError(`Erreur de lecture: ${status.error}`);
              await executePostTTSAction(); // Exécuter l'action même si l'audio échoue
            }
            return;
          }
          if (status.didJustFinish && !status.isLooping) {
            console.log("Lecture audio terminée.");
            await sound.unloadAsync(); // Décharger le son après lecture
            soundRef.current = null;
            await executePostTTSAction();
          }
        });

        console.log("Chargement et lecture du son de la réponse...");
        await sound.loadAsync({ uri: mp3Path });
        await sound.playAsync();
      } else {
        // S'il n'y a pas d'audio (ex: juste une action sans réponse vocale, ou erreur TTS backend)
        console.log("Pas d'audio à jouer pour la réponse.");
        await executePostTTSAction(); // Exécuter directement l'action
      }

    } catch (err: any) {
      console.error('Erreur lors de l\'arrêt/traitement de l\'enregistrement:', err);
      let errorMessage = 'Erreur lors du traitement vocal.';
      if (err.response) { // Erreur Axios avec réponse du serveur
        console.error('Données de l\'erreur serveur:', err.response.data);
        errorMessage = `Erreur du serveur: ${err.response.data?.error || err.message}`;
      } else if (err.request) { // Erreur Axios sans réponse (ex: timeout, réseau)
        errorMessage = 'Pas de réponse du serveur. Vérifiez votre connexion.';
      } else { // Autre erreur JS
        errorMessage = err.message || errorMessage;
      }
      setError(errorMessage);
      // S'assurer que les états sont correctement réinitialisés
      setIsProcessing(false);
      if (isRecording) setIsRecording(false); // Si on pensait encore enregistrer
      setAudioLevel(0);
    }
  };

  const toggleRecording = async () => {
    // Utiliser l'état du store `isRecording` comme source de vérité
    if (isRecording) {
      await stopRecording();
    } else {
      await startRecording();
    }
  };

  return {
    // isRecording est déjà dans le store, on pourrait le retourner pour la commodité du composant UI direct
    // mais il est préférable de le lire depuis le store pour une source unique de vérité.
    // Si le composant UI utilisant ce hook n'a pas accès direct au store, alors retourner `isRecording` ici est ok.
    isRecording: isRecording, // Ou `!!recordingRef.current` si on préfère l'état local du ref
    error,
    toggleRecording,
    // Exposer les fonctions de démarrage/arrêt individuellement si nécessaire
    // startRecording,
    // stopRecording,
  };
}