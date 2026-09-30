import { create } from "zustand";

interface EditorState {
  draftName: string;
  selectedNodeId: string | null;
  setDraftName: (name: string) => void;
  selectNode: (id: string | null) => void;
  reset: () => void;
}

const initialState = { draftName: "", selectedNodeId: null };

// Ephemeral authoring state only. Server responses belong in TanStack Query.
export const useEditorStore = create<EditorState>((set) => ({
  ...initialState,
  setDraftName: (draftName) => set({ draftName }),
  selectNode: (selectedNodeId) => set({ selectedNodeId }),
  reset: () => set(initialState),
}));
