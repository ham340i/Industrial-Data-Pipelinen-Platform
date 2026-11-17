# UI mockups

The workbench was designed as clickable mockups in Figma before and alongside the React implementation.

**[Open the interactive prototype in Figma](https://www.figma.com/proto/TEqCFM0wG4vhOLN9gbMREe/Industrial-Data-Pipeline-Platform-%E2%80%94-UI-Mockups?node-id=3-13355&p=f&t=kXDvoY3o8ww6uROM-1&scaling=min-zoom&content-scaling=fixed&page-id=0%3A1&starting-point-node-id=3%3A9111&show-proto-sidebar=1)**

The prototype opens at its starting screen with the screen list in the left sidebar. Click through it in presentation mode, or pick a screen from the sidebar. Viewing needs only a browser; a Figma account is not required for a link shared with view access.

## How the mockups relate to the implementation

| Area in the workbench | Implemented in |
|---|---|
| Projects and navigation | [Projects.tsx](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/Projects.tsx), [App.tsx](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/App.tsx) |
| Pipeline builder canvas and block library | [Canvas.tsx](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/Canvas.tsx), [Builder.tsx](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/Builder.tsx) |
| Block configuration panel | [BlockConfigPanel.tsx](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/configuration/BlockConfigPanel.tsx) |
| Validation problems | [ValidationPanel.tsx](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/ValidationPanel.tsx) |
| Data preview | [PreviewPanel.tsx](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/PreviewPanel.tsx) |
| Run controls and run monitoring | [RunControls.tsx](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/RunControls.tsx), [RunMonitor.tsx](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/RunMonitor.tsx) |
| Workspace settings | [WorkspaceSettings.tsx](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/src/WorkspaceSettings.tsx) |

Where the built workbench differs from a mockup, the implementation and its tests are authoritative; record intended design changes as issues.

See also: [Overall architecture and class diagrams](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Architecture), [Personas](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Personas), [Diversity statement](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Diversity-Statement).
