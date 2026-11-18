// AI contribution: 50% or more AI-generated
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getWorkspace } from "./api/workspace";
import { useEditorStore } from "./state/editor";

export function WorkspaceSession() {
  const workspace = useQuery({
    queryKey: ["workspace-settings"],
    queryFn: getWorkspace,
    retry: false,
    refetchOnWindowFocus: false,
  });
  useEffect(() => {
    if (workspace.data)
      useEditorStore.getState().switchWorkspace(workspace.data.root_path);
  }, [workspace.data]);
  return null;
}
