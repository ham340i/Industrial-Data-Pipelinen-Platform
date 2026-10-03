import { expect, it } from "vitest";
import { useEditorStore } from "./editor";

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
