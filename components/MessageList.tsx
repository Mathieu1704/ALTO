import Colors from '@/constants/colors';
import { useChatStore } from '@/store/chat-store';
import { useSettingsStore } from '@/store/settings-store';
import { Message } from '@/types/chat';
import React, { useEffect, useRef } from 'react';
import { FlatList, StyleSheet, Text, View } from 'react-native';

export default function MessageList() {
  const { messages } = useChatStore();
  const { isDarkTheme } = useSettingsStore();
  const theme = isDarkTheme ? Colors.dark : Colors.light;

  const listRef = useRef<FlatList<Message>>(null);

  // Méthode fiable pour scroller tout en bas
  const scrollToBottom = () => {
    if (!listRef.current || messages.length === 0) return;
    try {
      listRef.current.scrollToIndex({
        index: messages.length - 1,
        animated: true
      });
    } catch {
      // fallback si index out of range
      listRef.current.scrollToEnd({ animated: true });
    }
  };

  // 1️⃣ À chaque fois que le tableau change, on descend
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const lastMessageId = messages[messages.length - 1]?.id;

  const renderMessage = ({ item }: { item: Message }) => {
    const isUser = item.role === 'user';
    const isLast = item.id === lastMessageId;

    return (
      <View
        // 2️⃣ Quand le layout du dernier message est terminé, on scroll
        onLayout={() => {
          if (isLast) {
            scrollToBottom();
          }
        }}
        style={[
          styles.messageContainer,
          isUser
            ? [styles.userMessage, { backgroundColor: theme.primary }]
            : [styles.assistantMessage, { backgroundColor: theme.card }]
        ]}
      >
        <Text style={[styles.messageText, { color: theme.text }]}>
          {item.content}
        </Text>
        <Text style={[styles.timestamp, { color: theme.subtext }]}>
          {new Date(item.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </Text>
      </View>
    );
  };

  return (
    <FlatList
      ref={listRef}
      data={messages}
      renderItem={renderMessage}
      keyExtractor={(item) => item.id}
      contentContainerStyle={styles.listContent}
      // 3️⃣ Si la taille du contenu change, on redescend aussi
      onContentSizeChange={() => scrollToBottom()}
      // 4️⃣ Au tout premier rendu, on est déjà en bas
      onLayout={() => scrollToBottom()}
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
