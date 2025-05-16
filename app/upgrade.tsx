import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';

export default function UpgradeScreen() {
  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Choisissez une offre</Text>

      <TouchableOpacity style={styles.card}>
        <Text style={styles.planTitle}>Premium</Text>
        <Text>10 €/mois – Plus d’options et confort</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.card}>
        <Text style={styles.planTitle}>Unlimited</Text>
        <Text>25 €/mois – Illimité et prioritaire</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.card}>
        <Text style={styles.planTitle}>25 interactions</Text>
        <Text>1 € – Recharge ponctuelle</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.card}>
        <Text style={styles.planTitle}>1 appel</Text>
        <Text>2 € – Assistance par téléphone</Text>
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
