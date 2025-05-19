import React from 'react';
import {
  StyleSheet,
  View,
  Text,
  Switch,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons'; // ✅ Ionicons importé
import Colors from '@/constants/colors';
import { useChatStore } from '@/store/chat-store';
import { useSettingsStore } from '@/store/settings-store';
import { useRouter } from 'expo-router';
import { useUserStore } from '@/store/user-store';

const { logout } = useUserStore();
const router = useRouter();

export default function SettingsScreen() {
  const { clearMessages } = useChatStore();
  const {
    isDarkTheme,
    enableNotifications,
    saveTranscripts,
    setIsDarkTheme,
    setEnableNotifications,
    setSaveTranscripts,
  } = useSettingsStore();

  const theme = isDarkTheme ? Colors.dark : Colors.light;
  const router = useRouter();

  return (
    <ScrollView style={[styles.container, { backgroundColor: theme.background }]}>
      <View style={[styles.section, { borderBottomColor: theme.border }]}>
        <Text style={[styles.sectionTitle, { color: theme.text }]}>Apparence</Text>
        <View style={styles.settingItem}>
          <Text style={[styles.settingLabel, { color: theme.text }]}>Thème sombre</Text>
          <Switch
            value={isDarkTheme}
            onValueChange={setIsDarkTheme}
            trackColor={{ false: theme.inactive, true: theme.primary }}
            thumbColor={theme.text}
          />
        </View>
      </View>

      <View style={[styles.section, { borderBottomColor: theme.border }]}>
        <Text style={[styles.sectionTitle, { color: theme.text }]}>Notifications</Text>
        <View style={styles.settingItem}>
          <Text style={[styles.settingLabel, { color: theme.text }]}>Activer les notifications</Text>
          <Switch
            value={enableNotifications}
            onValueChange={setEnableNotifications}
            trackColor={{ false: theme.inactive, true: theme.primary }}
            thumbColor={theme.text}
          />
        </View>
      </View>

      <View style={[styles.section, { borderBottomColor: theme.border }]}>
        <Text style={[styles.sectionTitle, { color: theme.text }]}>Privacy</Text>
        <View style={styles.settingItem}>
          <Text style={[styles.settingLabel, { color: theme.text }]}>Sauver les Voice Transcripts</Text>
          <Switch
            value={saveTranscripts}
            onValueChange={setSaveTranscripts}
            trackColor={{ false: theme.inactive, true: theme.primary }}
            thumbColor={theme.text}
          />
        </View>
      </View>

      <View style={[styles.section, { borderBottomColor: theme.border }]}>
        <Text style={[styles.sectionTitle, { color: theme.text }]}>Données</Text>
        <TouchableOpacity
          style={[
            styles.dangerButton,
            {
              backgroundColor: isDarkTheme
                ? 'rgba(255, 69, 58, 0.2)'
                : 'rgba(255, 69, 58, 0.1)',
            },
          ]}
          onPress={clearMessages}
        >
          <Ionicons
            name="trash-outline"
            size={18}
            color={theme.text}
            style={styles.buttonIcon}
          />
          <Text style={[styles.dangerButtonText, { color: theme.text }]}>
            Effacer l'historique des conversations
          </Text>
        </TouchableOpacity>
      </View>

      <View style={[styles.section, { borderBottomColor: theme.border }]}>
        <Text style={[styles.sectionTitle, { color: theme.text }]}>À propos</Text>
        <View style={styles.infoContainer}>
          <Ionicons
            name="information-circle-outline"
            size={20}
            color={theme.subtext}
            style={styles.infoIcon}
          />
          <View>
            <Text style={[styles.appName, { color: theme.text }]}>Alto</Text>
            <Text style={[styles.appVersion, { color: theme.subtext }]}>
              Version 1.0.0
            </Text>
            <Text style={[styles.appDescription, { color: theme.text }]}>
              Application d'assistance avec synthèse vocale en temps réel.
            </Text>
          </View>
        </View>
      </View>
      <View style={[styles.section, { borderBottomColor: theme.border }]}>
        <Text style={[styles.sectionTitle, { color: theme.text }]}>Abonnement</Text>
        <TouchableOpacity
          style={[styles.settingItem, styles.upgradeButton, { backgroundColor: theme.primary }]}
          onPress={() => {
            // Navigue vers un nouvel écran (à créer) ou ouvre une modale
            router.push('/upgrade');
            console.log("Bouton Upgrade pressé");
          }}
        >
          <Ionicons name="rocket-outline" size={20} color="#fff" style={{ marginRight: 10 }} />
          <Text style={{ color: '#fff', fontWeight: 'bold' }}>Passer à une version supérieure</Text>
        </TouchableOpacity>
      </View>
      <View style={[styles.section, { borderBottomColor: theme.border }]}>
        <Text style={[styles.sectionTitle, { color: theme.text }]}>Déconnexion</Text>
        <TouchableOpacity
          style={[styles.settingItem, styles.upgradeButton, { backgroundColor: theme.primary }]}
          onPress={() => {
            // Navigue vers un nouvel écran (à créer) ou ouvre une modale
            logout();
            router.replace('./(auth)/login');
          }}
        >
          <Text style={{ color: '#fff', fontWeight: 'bold' }}>Se déconnecter</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  section: {
    padding: 16,
    borderBottomWidth: 1,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  settingItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
  },
  settingLabel: {
    fontSize: 16,
  },
  dangerButton: {
    padding: 12,
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  dangerButtonText: {
    fontSize: 16,
    fontWeight: '500',
  },
  buttonIcon: {
    marginRight: 8,
  },
  infoContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  infoIcon: {
    marginRight: 12,
    marginTop: 4,
  },
  appName: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  appVersion: {
    fontSize: 14,
    marginBottom: 8,
  },
  appDescription: {
    fontSize: 14,
    lineHeight: 20,
  },
  upgradeButton: {
  marginTop: 10,
  padding: 15,
  borderRadius: 10,
  flexDirection: 'row',
  alignItems: 'center',
  justifyContent: 'center',
  },
});
