import { useMemo, useState } from "react";
import {
  Box,
  Checkbox,
  Collapse,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  TextField,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";

export type Leaf = { index: number; path: string[] };

type Node = {
  id: string;
  label: string;
  children: Node[];
  leaves: number[];
};

function buildTree(leaves: Leaf[]): Node {
  const root: Node = { id: "root", label: "root", children: [], leaves: [] };
  const getOrCreateChild = (parent: Node, label: string, id: string) => {
    let child = parent.children.find((c) => c.label === label);
    if (!child) {
      child = { id, label, children: [], leaves: [] };
      parent.children.push(child);
    }
    return child;
  };

  for (const leaf of leaves) {
    let current = root;
    current.leaves.push(leaf.index);
    leaf.path.forEach((segment, depth) => {
      const id = `${current.id}/${depth}:${segment}`;
      current = getOrCreateChild(current, segment, id);
      current.leaves.push(leaf.index);
    });
  }

  return root;
}

function uniqueSorted(nums: number[]) {
  return Array.from(new Set(nums)).sort((a, b) => a - b);
}

export default function TreeMultiSelect({
  leaves,
  selected,
  onChange,
  placeholder,
}: {
  leaves: Leaf[];
  selected: number[];
  onChange: (sel: number[]) => void;
  placeholder?: string;
}) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [q, setQ] = useState("");

  const tree = useMemo(() => buildTree(leaves), [leaves]);
  const selectedSet = useMemo(() => new Set(selected), [selected]);

  const filteredLeaves = useMemo(() => {
    const qq = q.trim().toLowerCase();
    if (!qq) return leaves;
    return leaves.filter((l) => l.path.join(" / ").toLowerCase().includes(qq));
  }, [leaves, q]);

  const filteredTree = useMemo(() => buildTree(filteredLeaves), [filteredLeaves]);

  const toggleNode = (node: Node) => {
    const allSelected = node.leaves.every((i) => selectedSet.has(i));
    const next = new Set(selectedSet);
    if (allSelected) {
      node.leaves.forEach((i) => next.delete(i));
    } else {
      node.leaves.forEach((i) => next.add(i));
    }
    onChange(uniqueSorted(Array.from(next)));
  };

  const renderNode = (node: Node, depth: number) => {
    if (node.id === "root") {
      return node.children.map((c) => renderNode(c, depth));
    }

    const hasChildren = node.children.length > 0;
    const isExpanded = expanded[node.id] ?? false;
    const allSelected = node.leaves.length > 0 && node.leaves.every((i) => selectedSet.has(i));
    const someSelected = node.leaves.some((i) => selectedSet.has(i));

    return (
      <Box key={node.id}>
        <ListItem dense disableGutters sx={{ pl: depth * 1.5 }}>
          {hasChildren ? (
            <IconButton
              size="small"
              onClick={() => setExpanded((s) => ({ ...s, [node.id]: !isExpanded }))}
              aria-label={isExpanded ? "collapse" : "expand"}
            >
              {isExpanded ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
            </IconButton>
          ) : (
            <Box sx={{ width: 32 }} />
          )}

          <ListItemIcon sx={{ minWidth: 34 }}>
            <Checkbox
              size="small"
              checked={allSelected}
              indeterminate={!allSelected && someSelected}
              onChange={() => toggleNode(node)}
            />
          </ListItemIcon>
          <ListItemText primary={node.label} />
        </ListItem>
        {hasChildren ? (
          <Collapse in={isExpanded} timeout="auto" unmountOnExit>
            <List disablePadding>
              {node.children
                .slice()
                .sort((a, b) => a.label.localeCompare(b.label))
                .map((c) => renderNode(c, depth + 1))}
            </List>
          </Collapse>
        ) : null}
      </Box>
    );
  };

  return (
    <Box>
      <TextField
        size="small"
        fullWidth
        placeholder={placeholder ?? "Search…"}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        sx={{ mb: 1 }}
      />
      <List dense disablePadding>
        {renderNode(filteredTree, 0)}
      </List>
    </Box>
  );
}
