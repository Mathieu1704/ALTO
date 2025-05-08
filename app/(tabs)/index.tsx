import React from 'react';
import { StyleSheet, View, Text, Platform } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import VoiceVisualizer from '@/components/VoiceVisualizer';
import PhoneNumberDisplay from '@/components/PhoneNumberDisplay';
import MessageList from '@/components/MessageList';
import useVoiceRecognition from '@/hooks/useVoiceRecognition';
import Colors from '@/constants/colors';
import { useSettingsStore } from '@/store/settings-store';

export default function HomeScreen() {
  const { toggleRecording, error } = useVoiceRecognition();
  const { isDarkTheme } = useSettingsStore();
  const theme = isDarkTheme ? Colors.dark : Colors.light;

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={isDarkTheme ? "light" : "dark"} />
      
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.text }]}>Alto</Text>
        <Text style={[styles.subtitle, { color: theme.subtext }]}>Voice-Reactive AI Assistant</Text>
      </View>
      
      <View style={styles.phoneSection}>
        <PhoneNumberDisplay />
      </View>
      
      <View style={styles.visualizerContainer}>
        <VoiceVisualizer size={220} onPress={toggleRecording} />
      </View>
      
      <View style={[styles.messageContainer, { 
        borderTopColor: theme.border,
        backgroundColor: theme.background 
      }]}>
        <MessageList />
      </View>
      
      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingTop: 16,
    paddingBottom: 8,
    alignItems: 'center',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
  },
  subtitle: {
    fontSize: 14,
    marginTop: 4,
  },
  phoneSection: {
    width: '100%',
  },
  visualizerContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 20,
  },
  messageContainer: {
    flex: 1,
    borderTopWidth: 1,
  },
  errorContainer: {
    padding: 12,
    backgroundColor: Colors.dark.accent,
    marginHorizontal: 16,
    borderRadius: 8,
    marginBottom: 16,
  },
  errorText: {
    color: Colors.dark.text,
    textAlign: 'center',
  },
});