"use client";

import React, { useState, useCallback } from "react";
import {
  Handle,
  Position,
  useNodeId,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import * as SubframeCore from "@subframe/core";
import { ToggleGroup } from "../../../../frontend/src/subframe/components/ToggleGroup";
import { Button } from "../../../../frontend/src/subframe/components/Button";
import { Table } from "../../../../frontend/src/subframe/components/Table";
import { Select } from "../../../../frontend/src/subframe/components/Select";
import { TextField } from "../../../../frontend/src/subframe/components/TextField";
import { PropertiesAccordion } from "../../../../frontend/src/subframe/components/PropertiesAccordion";
import { TextArea } from "../../../../frontend/src/subframe/components/TextArea";
import { Alert } from "../../../../frontend/src/subframe/components/Alert";
import { PropertiesRow } from "../../../../frontend/src/subframe/components/PropertiesRow";
import { Switch } from "../../../../frontend/src/subframe/components/Switch";
import { type NodeResults } from "@/types/index";
import { NodeLayout } from "@/components/nodes/index";
import { ConfigurationDrawer } from "../ConfigurationDrawer";

type PythonNode = Node<
  {
    title: string;
    nodeType: string;
    results: NodeResults;
    onNodeOpen: (node_id: string) => void;
  },
  "python"
>;

export default function PythonNode(props: NodeProps<PythonNode>) {
  const nodeId = useNodeId();

  function onNodeOpen() {
    props.data.onNodeOpen(nodeId as string);
  }

  return (
    <NodeLayout
      openNode={onNodeOpen}
      title={props.data.title}
      results={props.data.results}
      isSelected={props.selected || false}
      nodeType={props.type}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-4 !h-4 !bg-brand-600"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="a"
        className="!w-4 !h-4 !bg-brand-600"
      />
      <div className="flex flex-col w-full select-text gap-4">
        <span className="text-heading-3 font-heading-3 text-default-font">
          Code
        </span>
        <div className="flex w-full flex-col items-start gap-4 rounded bg-neutral-50 pt-2 pr-2 pb-2 pl-2">
          <span className="w-full whitespace-pre-wrap text-monospace-body font-monospace-body text-default-font">
            {"// Add a bit of code here\n\n// And some more if needed..."}
          </span>
        </div>
      </div>
    </NodeLayout>
  );
}

interface PythonNodeConfigurationDrawerProps {
  closeDrawer: () => void;
}

export function PythonNodeConfigurationDrawer() {
  return (
    <div>
      <PropertiesAccordion title="Python Version">
        <Select
          className="h-auto w-full flex-none"
          label=""
          placeholder="python3.10"
          helpText=""
          value=""
          onValueChange={(value: string) => {}}
        >
          <Select.Item value="Item 1">Item 1</Select.Item>
          <Select.Item value="Item 2">Item 2</Select.Item>
          <Select.Item value="Item 3">Item 3</Select.Item>
        </Select>
      </PropertiesAccordion>
      <PropertiesAccordion title="Dependencies">
        <div className="flex flex-col items-start gap-4">
          <span className="text-caption font-caption text-default-font">
            You can specify python packages to import during the execution of
            this workflow. Imported packages will be available across all nodes
            in this workflow.
          </span>
          <div className="flex items-center gap-4">
            <span className="text-caption font-caption text-default-font">
              Package Manager
            </span>
            <ToggleGroup value="" onValueChange={(value: string) => {}}>
              <ToggleGroup.Item icon={null} value="dfe802fe">
                Poetry
              </ToggleGroup.Item>
              <ToggleGroup.Item icon={null} value="69510ce2">
                Pip
              </ToggleGroup.Item>
            </ToggleGroup>
          </div>
          <div className="flex w-full flex-col items-start gap-4 rounded bg-neutral-50 pt-2 pr-2 pb-2 pl-2">
            <span className="w-full whitespace-pre-wrap text-monospace-body font-monospace-body text-default-font">
              {
                'python = ">=3.10,<3.12"\nfastapi = "^0.111.0"\nuvicorn = "^0.20.0"\npython-dotenv = "^0.21.1"\npydantic = "^2.7.1"\nlangchain = "^0.0.317"\nstrenum = "^0.4.15"\nqdrant-client = "^1.3.1"'
              }
            </span>
          </div>
        </div>
        <div className="flex w-full items-center gap-2 pt-4">
          <Button
            variant="neutral-primary"
            onClick={(event: React.MouseEvent<HTMLButtonElement>) => {}}
          >
            Install Packages
          </Button>
        </div>
      </PropertiesAccordion>
      <PropertiesAccordion title="Sample Data">
        <div className="flex flex-col items-start gap-2">
          <Button
            variant="neutral-secondary"
            icon="FeatherUpload"
            onClick={(event: React.MouseEvent<HTMLButtonElement>) => {}}
          >
            Upload
          </Button>
          <span className="text-caption font-caption text-subtext-color">
            Upload a CSV file to test this node with sample input data.
          </span>
        </div>
      </PropertiesAccordion>
      <PropertiesRow text="Run Schedule">
        <Select
          variant="filled"
          label=""
          placeholder="24 hours"
          helpText=""
          value=""
          onValueChange={(value: string) => {}}
        >
          <Select.Item value="5 mins">5 mins</Select.Item>
          <Select.Item value="30 mins">30 mins</Select.Item>
          <Select.Item value="1 hour">1 hour</Select.Item>
        </Select>
      </PropertiesRow>
      <PropertiesRow text="On Failure">
        <Select
          variant="filled"
          label=""
          placeholder="Retry"
          helpText=""
          value=""
          onValueChange={(value: string) => {}}
        >
          <Select.Item value="5 mins">5 mins</Select.Item>
          <Select.Item value="Notify">Notify</Select.Item>
          <Select.Item value="Ignore">Ignore</Select.Item>
        </Select>
      </PropertiesRow>
    </div>
  );
}