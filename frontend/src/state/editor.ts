import { create } from "zustand";

interface EditorState {
  draftName: string;
  selectedNodeId: string | null;
  projectId: string | null;
  setProject: (id: string | null) => void;
  setDraftName: (name: string) => void;
  selectNode: (id: string | null) => void;
  reset: () => void;
}

const initialState = { draftName: "", selectedNodeId: null, projectId: null };

// Ephemeral authoring state only. Server responses belong in TanStack Query.
export const useEditorStore = create<EditorState>((set) => ({
  ...initialState,
  setProject: (projectId) =>
    set((state) =>
      state.projectId === projectId ? state : { ...initialState, projectId },
    ),
  setDraftName: (draftName) => set({ draftName }),
  selectNode: (selectedNodeId) => set({ selectedNodeId }),
  reset: () => set(initialState),
}));
