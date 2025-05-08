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

  return (
    <ScrollView style={[styles.container, { backgroundColor: theme.background }]}>
      <View style={[styles.section, { borderBottomColor: theme.border }]}>
        <Text style={[styles.sectionTitle, { color: theme.text }]}>Appearance</Text>
        <View style={styles.settingItem}>
          <Text style={[styles.settingLabel, { color: theme.text }]}>Dark Theme</Text>
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
          <Text style={[styles.settingLabel, { color: theme.text }]}>Enable Notifications</Text>
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
          <Text style={[styles.settingLabel, { color: theme.text }]}>Save Voice Transcripts</Text>
          <Switch
            value={saveTranscripts}
            onValueChange={setSaveTranscripts}
            trackColor={{ false: theme.inactive, true: theme.primary }}
            thumbColor={theme.text}
          />
        </View>
      </View>

      <View style={[styles.section, { borderBottomColor: theme.border }]}>
        <Text style={[styles.sectionTitle, { color: theme.text }]}>Data</Text>
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
            Clear Conversation History
          </Text>
        </TouchableOpacity>
      </View>

      <View style={[styles.section, { borderBottomColor: theme.border }]}>
        <Text style={[styles.sectionTitle, { color: theme.text }]}>About</Text>
        <View style={styles.infoContainer}>
          <Ionicons
            name="information-circle-outline"
            size={20}
            color={theme.subtext}
            style={styles.infoIcon}
          />
          <View>
            <Text style={[styles.appName, { color: theme.text }]}>VoixActive</Text>
            <Text style={[styles.appVersion, { color: theme.subtext }]}>
              Version 1.0.0
            </Text>
            <Text style={[styles.appDescription, { color: theme.text }]}>
              A voice-reactive chat application that visualizes your voice and
              connects to AI for intelligent conversations.
            </Text>
          </View>
        </View>
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
});
