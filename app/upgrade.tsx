import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import Colors from '@/constants/colors';
import { useSettingsStore } from '@/store/settings-store';

export default function UpgradeScreen() {
  const { isDarkTheme } = useSettingsStore();
  const theme = isDarkTheme ? Colors.dark : Colors.light;

  return (
    <ScrollView style={[styles.container, { backgroundColor: theme.background }]}>
      <Text style={[styles.title, { color: theme.text }]}>Choisissez une offre</Text>

      <TouchableOpacity style={[styles.card, { backgroundColor: theme.card }]}>
        <Text style={[styles.planTitle, { color: theme.text }]}>Premium</Text>
        <Text style={{ color: theme.subtext }}>10 €/mois – Assistance plus élaborée et 400 interactions par mois</Text>
      </TouchableOpacity>

      <TouchableOpacity style={[styles.card, { backgroundColor: theme.card }]}>
        <Text style={[styles.planTitle, { color: theme.text }]}>Unlimited</Text>
        <Text style={{ color: theme.subtext }}>25 €/mois – Nombre d'interactions illimité et 3 appels à l'assistance téléphonique par mois</Text>
      </TouchableOpacity>

      <TouchableOpacity style={[styles.card, { backgroundColor: theme.card }]}>
        <Text style={[styles.planTitle, { color: theme.text }]}>25 interactions</Text>
        <Text style={{ color: theme.subtext }}>1 € – Recharge ponctuelle</Text>
      </TouchableOpacity>

      <TouchableOpacity style={[styles.card, { backgroundColor: theme.card }]}>
        <Text style={[styles.planTitle, { color: theme.text }]}>1 appel</Text>
        <Text style={{ color: theme.subtext }}>2 € – Assistance téléphonique</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: '#fff' },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 20 },
  card: {
    backgroundColor: '#eee',
    padding: 15,
    marginBottom: 15,
    borderRadius: 10,
  },
  planTitle: { fontSize: 18, fontWeight: 'bold' },
});
