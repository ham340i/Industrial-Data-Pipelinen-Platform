import { expect, it } from "vitest";
import { useEditorStore } from "./editor";

it("clears an unsaved draft when switching project identity", () => {
  const store = useEditorStore.getState();
  store.setProject("project-a");
  store.setDraftName("Draft A");
  store.selectNode("node-a");
  store.setProject("project-a");
  expect(useEditorStore.getState().draftName).toBe("Draft A");
  store.setProject("project-b");
  expect(useEditorStore.getState()).toMatchObject({
    projectId: "project-b",
    draftName: "",
    selectedNodeId: null,
  });
});

it("resets unsaved name and selection together without persisting remote data", () => {
  useEditorStore.getState().setDraftName("Synthetic draft");
  useEditorStore.getState().selectNode("node-1");
  expect(useEditorStore.getState()).toMatchObject({
    draftName: "Synthetic draft",
    selectedNodeId: "node-1",
  });
  useEditorStore.getState().reset();
  expect(useEditorStore.getState()).toMatchObject({
    draftName: "",
    selectedNodeId: null,
  });
});
