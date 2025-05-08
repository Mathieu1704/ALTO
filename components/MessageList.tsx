import React from 'react';
import { View, Text, StyleSheet, FlatList } from 'react-native';
import { Message } from '@/types/chat';
import Colors from '@/constants/colors';
import { useChatStore } from '@/store/chat-store';
import { useSettingsStore } from '@/store/settings-store';

export default function MessageList() {
  const { messages } = useChatStore();
  const { isDarkTheme } = useSettingsStore();
  const theme = isDarkTheme ? Colors.dark : Colors.light;

  const renderMessage = ({ item }: { item: Message }) => {
    const isUser = item.role === 'user';

    return (
      <View style={[
        styles.messageContainer,
        isUser
          ? [styles.userMessage, { backgroundColor: theme.primary }]
          : [styles.assistantMessage, { backgroundColor: theme.card }]
      ]}>
        <Text style={[styles.messageText, { color: theme.text }]}>{item.content}</Text>
        <Text style={[styles.timestamp, { color: theme.subtext }]}>
          {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </Text>
      </View>
    );
  };

  return (
    <FlatList
      data={messages}
      renderItem={renderMessage}
      keyExtractor={(item) => item.id}
      contentContainerStyle={styles.listContent}
      inverted={false} 
    />
  );
}

const styles = StyleSheet.create({
  listContent: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  messageContainer: {
    maxWidth: '80%',
    marginVertical: 4,
    padding: 12,
    borderRadius: 16,
  },
  userMessage: {
    alignSelf: 'flex-end',
    borderBottomRightRadius: 4,
  },
  assistantMessage: {
    alignSelf: 'flex-start',
    borderBottomLeftRadius: 4,
  },
  messageText: {
    fontSize: 16,
  },
  timestamp: {
    fontSize: 10,
    alignSelf: 'flex-end',
    marginTop: 4,
  },
});
