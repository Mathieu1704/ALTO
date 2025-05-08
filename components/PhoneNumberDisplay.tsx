import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Linking,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import Colors from '@/constants/colors';
import { useChatStore } from '@/store/chat-store';
import { useSettingsStore } from '@/store/settings-store';

export default function PhoneNumberDisplay() {
  const { phoneNumber } = useChatStore();
  const { isDarkTheme } = useSettingsStore();
  const theme = isDarkTheme ? Colors.dark : Colors.light;

  const belgianNumber = '+32 487214255';

  const handleCall = async () => {
    // ✅ Vibration uniquement
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);

    Alert.alert(
      'Appel d’urgence',
      'Souhaitez-vous appeler la centrale de secours ?',
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Appeler',
          style: 'destructive',
          onPress: async () => {
            try {
              const phoneUrl = `tel:${belgianNumber.replace(/\s/g, '')}`;
              const canOpen = await Linking.canOpenURL(phoneUrl);
              if (canOpen) {
                await Linking.openURL(phoneUrl);
              } else {
                console.log('Impossible d’ouvrir l’application téléphone');
              }
            } catch (error) {
              console.error('Erreur lors de l’appel :', error);
            }
          },
        },
      ],
      { cancelable: true }
    );
  };

  return (
    <View style={styles.container}>
      <Text style={[styles.infoText, { color: theme.subtext }]}>
        En cas d’urgence, contactez la centrale :
      </Text>

      <TouchableOpacity
        style={styles.phoneContainer}
        onPress={handleCall}
        activeOpacity={0.85}
      >
        <Ionicons
          name="call-outline"
          size={20}
          color="white"
          style={styles.icon}
        />
        <Text style={styles.phoneNumber}>{belgianNumber}</Text>
        <Text style={styles.sosText}>SOS</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    paddingHorizontal: 20,
    marginVertical: 20,
  },
  infoText: {
    fontSize: 14,
    marginBottom: 8,
    textAlign: 'center',
  },
  phoneContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#e53935',
  },
  icon: {
    marginRight: 8,
  },
  phoneNumber: {
    fontSize: 16,
    fontWeight: '600',
    color: 'white',
    marginRight: 10,
  },
  sosText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: 'white',
  },
});
