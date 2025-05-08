import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  StyleSheet,
  Animated,
  Easing,
  TouchableOpacity,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { useChatStore } from '@/store/chat-store';
import { useSettingsStore } from '@/store/settings-store';
import Colors from '@/constants/colors';

interface VoiceVisualizerProps {
  size?: number;
  onPress: () => void;
}

export default function VoiceVisualizer({ size = 200, onPress }: VoiceVisualizerProps) {
  const { isRecording, audioLevel, isProcessing } = useChatStore();
  const { isDarkTheme } = useSettingsStore();
  const theme = isDarkTheme ? Colors.dark : Colors.light;

  const pulseAnim = useRef(new Animated.Value(1)).current;
  const processingAnim = useRef(new Animated.Value(0)).current;

  const waves = Array.from({ length: 5 }, () => useRef(new Animated.Value(0)).current);

  const smoothedLevel = useRef(0);
  const waveAnims = useRef<Animated.CompositeAnimation[]>([]);

  useEffect(() => {
    if (isRecording) {
      smoothedLevel.current = smoothedLevel.current * 0.7 + audioLevel * 0.3;
      Animated.timing(pulseAnim, {
        toValue: 1 + smoothedLevel.current * 0.3,
        duration: 200,
        useNativeDriver: true,
        easing: Easing.bezier(0.25, 0.1, 0.25, 1),
      }).start();
      startWaveAnimations();
    } else {
      Animated.timing(pulseAnim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
        easing: Easing.bezier(0.25, 0.1, 0.25, 1),
      }).start();
      stopWaveAnimations();
    }
  }, [isRecording, audioLevel]);

  useEffect(() => {
    if (isProcessing) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(processingAnim, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: true,
            easing: Easing.inOut(Easing.sin),
          }),
          Animated.timing(processingAnim, {
            toValue: 0,
            duration: 1000,
            useNativeDriver: true,
            easing: Easing.inOut(Easing.sin),
          }),
        ])
      ).start();
    } else {
      processingAnim.setValue(0);
    }
  }, [isProcessing]);

  const startWaveAnimations = () => {
    stopWaveAnimations();
    waves.forEach((wave, i) => {
      const anim = Animated.loop(
        Animated.sequence([
          Animated.timing(wave, {
            toValue: 1,
            duration: 1500 + i * 300,
            useNativeDriver: true,
            easing: Easing.out(Easing.ease),
          }),
          Animated.timing(wave, {
            toValue: 0,
            duration: 0,
            useNativeDriver: true,
          }),
        ])
      );
      anim.start();
      waveAnims.current.push(anim);
    });
  };

  const stopWaveAnimations = () => {
    waveAnims.current.forEach((anim) => anim.stop());
    waveAnims.current = [];
    waves.forEach((wave) => wave.setValue(0));
  };

  const handlePress = () => {
    if (Platform.OS !== 'web') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    }
    onPress();
  };

  const circleSize = size;
  const innerSize = circleSize * 0.8;

  const getWaveStyle = (wave: Animated.Value, index: number) => {
    const factor = 0.2 + index * 0.05;
    return {
      opacity: isRecording ? Animated.multiply(wave, 0.4) : 0,
      transform: [
        {
          scale: Animated.add(1, Animated.multiply(wave, factor)),
        },
      ],
    };
  };

  return (
    <TouchableOpacity
      style={[styles.container, { width: circleSize, height: circleSize }]}
      onPress={handlePress}
      activeOpacity={0.8}
    >
      {waves.map((wave, i) => (
        <Animated.View
          key={i}
          style={[
            styles.waveCircle,
            {
              width: circleSize * (1.1 + i * 0.15),
              height: circleSize * (1.1 + i * 0.15),
              borderRadius: (circleSize * (1.1 + i * 0.15)) / 2,
              borderColor: theme.primary,
            },
            getWaveStyle(wave, i),
          ]}
        />
      ))}

      <Animated.View
        style={[styles.outerCircle, {
          width: circleSize,
          height: circleSize,
          borderRadius: circleSize / 2,
          backgroundColor: isRecording ? theme.accent : theme.primary,
          transform: [{ scale: pulseAnim }],
          opacity: isProcessing ? 0.7 : 1,
        }]}
      />

      <View
        style={[styles.innerCircle, {
          width: innerSize,
          height: innerSize,
          borderRadius: innerSize / 2,
          backgroundColor: isRecording ? theme.accent : theme.primary,
        }]}
      >
        <View style={styles.iconContainer}>
          <Ionicons name={isRecording ? 'stop' : 'mic'} size={24} color="#FFFFFF" />
        </View>
      </View>

      {isProcessing && (
        <Animated.View
          style={[styles.processingIndicator, {
            width: innerSize * 0.9,
            height: innerSize * 0.9,
            borderRadius: (innerSize * 0.9) / 2,
            backgroundColor: theme.secondary,
            opacity: processingAnim,
          }]}
        />
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  outerCircle: {
    position: 'absolute',
    opacity: 0.3,
  },
  innerCircle: {
    position: 'absolute',
    alignItems: 'center',
    justifyContent: 'center',
  },
  processingIndicator: {
    position: 'absolute',
    opacity: 0.5,
  },
  waveCircle: {
    position: 'absolute',
    borderWidth: 2,
    borderStyle: 'solid',
  },
  iconContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
