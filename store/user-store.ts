import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UserState {
    id: string | null;
    email: string | null;
    setUser : (user: { id: string, email: string}) => void;
    logout: () => void;
}

export const useUserStore = create<UserState>()(
    persist(
        (set) => ({
            id: null,
            email: null,
            setUser: ({ id, email }) => set({ id, email }),
            logout: () => set({ id: null, email: null}),
        }),
        { name: 'user-storage' }
    )
);