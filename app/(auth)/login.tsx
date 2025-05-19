import React, { use, useState } from 'react';
import { View, Text, TextInput, Button, StyleSheet, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { useUserStore } from '@/store/user-store';
import Colors from '@/constants/colors';
import { useSettingsStore } from '@/store/settings-store';

export default function LoginScreen() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const setUser = useUserStore((s) => s.setUser);
    const router = useRouter();

    const isDarkTheme = useSettingsStore((s) => s.isDarkTheme);
    const theme = isDarkTheme ? Colors.dark : Colors.light;

    const handleLogin = async() => {
        try {
            const res = await fetch('https://BACKEND_URL/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({email, password}),
            });

            const data = await res.json();
            if (data.success) {
                setUser({ id: data.user_id, email });
                router.replace('/');
            } else {
                Alert.alert('Erreur', 'Identifiants incorrects');
            }
        } catch {
            Alert.alert('Erreur', 'Connexion impossible au serveur');
        }
    };

    return (
        <View style={[styles.container, { backgroundColor: theme.background }]}>
            <Text style={[styles.title, { color: theme.text }]}>Connexion</Text>
            <TextInput
            placeholder="Email"
            placeholderTextColor={theme.subtext}
            value={email}
            onChangeText={setEmail}
            style={[styles.input, { color: theme.text, borderColor: theme.border }]}
            />
            <TextInput
            placeholder="Mot de passe"
            placeholderTextColor={theme.subtext}
            value={password}
            secureTextEntry
            onChangeText={setPassword}
            style={[styles.input, { color: theme.text, borderColor: theme.border }]}
            />
            <Button title="Se connecter" onPress={handleLogin} />
        </View> 
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, justifyContent: 'center', padding: 20 },
    title: { fontSize: 24, fontWeight: 'bold', marginBottom: 20, textAlign: 'center' },
    input: { borderWidth: 1, borderColor: '#ccc', padding: 10, marginBottom: 15, borderRadius: 5},
});