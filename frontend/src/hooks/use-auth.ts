"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { fetchMe, login, logout, type Me, tokenStore } from "@/lib/api";

export function useMe() {
  return useQuery<Me>({
    queryKey: ["me"],
    queryFn: fetchMe,
    enabled: typeof window !== "undefined" && !!tokenStore.access,
    retry: false,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      login(email, password),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["me"] });
      router.push("/dashboard");
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      qc.clear();
      router.push("/login");
    },
  });
}
