import { useUserStore } from '@/store/user-store';
import { useEffect } from 'react';
import { useRouter } from 'expo-router';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
    const id = useUserStore((s) => s.id);
    const router = useRouter();

    useEffect(() => {
        if (!id) router.replace('./(auth)/login');
    }, [id]);

    if(!id) return null;
    return <>{children}</>;
}
