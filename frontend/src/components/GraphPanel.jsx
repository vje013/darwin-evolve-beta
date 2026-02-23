import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  Box, Typography, Chip, Tooltip, IconButton, CircularProgress,
  Select, MenuItem, FormControl, InputLabel,
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import ZoomInIcon from '@mui/icons-material/ZoomIn'
import ZoomOutIcon from '@mui/icons-material/ZoomOut'
import CenterFocusStrongIcon from '@mui/icons-material/CenterFocusStrong'
import { getGraphData } from '../api/client'

const TYPE_COLORS = {
  Repository: '#238636',
  Branch: '#2ea043',
  File: '#8b949e',
  PullRequest: '#a371f7',
  Issue: '#f85149',
  Commit: '#58a6ff',
  FigmaFile: '#a259ff',
  FigmaPage: '#c084fc',
  FigmaFrame: '#d8b4fe',
  FigmaComponent: '#e9d5ff',
  Component: '#6ee7b7',
  Requirement: '#fbbf24',
  Tool: '#38bdf8',
  PRD: '#6ee7b7',
  DecisionLog: '#fbbf24',
  TraceabilityMatrix: '#818cf8',
  DriftDetection: '#f87171',
  ReleaseNotes: '#38bdf8',
}

const SOURCE_SHAPES = {
  github: 'circle',
  figma: 'diamond',
  chat_extraction: 'square',
  artifact: 'star',
}

export default function GraphPanel({ roomId }) {
  const svgRef = useRef(null)
  const [graphData, setGraphData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [selectedNode, setSelectedNode] = useState(null)
  const [filterType, setFilterType] = useState('all')
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 })
  const simulationRef = useRef(null)
  const nodesRef = useRef([])
  const linksRef = useRef([])

  const load = async () => {
    setLoading(true)
    try {
      const data = await getGraphData(roomId)
      setGraphData(data)
    } catch (err) {
      console.error('Graph load error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [roomId])

  const drawGraph = useCallback(() => {
    if (!graphData || !svgRef.current) return

    const svg = svgRef.current
    const width = svg.clientWidth || 600
    const height = svg.clientHeight || 400

    // Filter nodes
    let nodes = graphData.nodes.map(n => ({ ...n }))
    if (filterType !== 'all') {
      const keepIds = new Set(nodes.filter(n => n.type === filterType).map(n => n.id))
      // Also keep nodes connected to filtered nodes
      graphData.links.forEach(l => {
        if (keepIds.has(l.source) || keepIds.has(l.source?.id)) keepIds.add(typeof l.target === 'string' ? l.target : l.target.id)
        if (keepIds.has(l.target) || keepIds.has(l.target?.id)) keepIds.add(typeof l.source === 'string' ? l.source : l.source.id)
      })
      nodes = nodes.filter(n => keepIds.has(n.id))
    }

    const nodeIds = new Set(nodes.map(n => n.id))
    const links = graphData.links
      .filter(l => nodeIds.has(l.source) && nodeIds.has(l.target))
      .map(l => ({ ...l }))

    nodesRef.current = nodes
    linksRef.current = links

    // Clear SVG
    while (svg.firstChild) svg.removeChild(svg.firstChild)

    // Create group for zoom/pan
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g')
    g.setAttribute('transform', `translate(${transform.x},${transform.y}) scale(${transform.k})`)
    svg.appendChild(g)

    // Draw links
    links.forEach(link => {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line')
      line.setAttribute('stroke', 'rgba(255,255,255,0.08)')
      line.setAttribute('stroke-width', '1')
      line.dataset.source = link.source
      line.dataset.target = link.target
      g.appendChild(line)
    })

    // Draw nodes
    nodes.forEach(node => {
      const group = document.createElementNS('http://www.w3.org/2000/svg', 'g')
      group.style.cursor = 'pointer'

      const color = TYPE_COLORS[node.type] || '#6b7280'
      const radius = node.type === 'Repository' ? 10 : node.type === 'Branch' ? 7 : 5

      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle')
      circle.setAttribute('r', radius)
      circle.setAttribute('fill', color)
      circle.setAttribute('stroke', 'rgba(0,0,0,0.3)')
      circle.setAttribute('stroke-width', '1')
      circle.setAttribute('opacity', '0.85')
      group.appendChild(circle)

      // Label (short name)
      const shortName = (node.name || '').split('/').pop().split(':').pop().substring(0, 20)
      if (radius >= 7 || nodes.length < 30) {
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text')
        text.setAttribute('dy', radius + 12)
        text.setAttribute('text-anchor', 'middle')
        text.setAttribute('fill', 'rgba(255,255,255,0.5)')
        text.setAttribute('font-size', '8')
        text.setAttribute('font-family', 'JetBrains Mono, monospace')
        text.textContent = shortName
        group.appendChild(text)
      }

      group.dataset.nodeId = node.id
      group.addEventListener('click', () => setSelectedNode(node))

      // Hover highlight
      group.addEventListener('mouseenter', () => {
        circle.setAttribute('stroke', '#6ee7b7')
        circle.setAttribute('stroke-width', '2')
        circle.setAttribute('opacity', '1')
      })
      group.addEventListener('mouseleave', () => {
        circle.setAttribute('stroke', 'rgba(0,0,0,0.3)')
        circle.setAttribute('stroke-width', '1')
        circle.setAttribute('opacity', '0.85')
      })

      g.appendChild(group)
      node._el = group
    })

    // Simple force simulation (no d3-force dependency — manual spring layout)
    // Initialize positions in a circle
    nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / nodes.length
      const r = Math.min(width, height) * 0.3
      node.x = width / 2 + r * Math.cos(angle)
      node.y = height / 2 + r * Math.sin(angle)
      node.vx = 0
      node.vy = 0
    })

    // Build adjacency for attraction
    const nodeMap = {}
    nodes.forEach(n => { nodeMap[n.id] = n })

    const tick = () => {
      const alpha = 0.3

      // Center gravity
      nodes.forEach(n => {
        n.vx += (width / 2 - n.x) * 0.001
        n.vy += (height / 2 - n.y) * 0.001
      })

      // Repulsion between all nodes
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x
          const dy = nodes[j].y - nodes[i].y
          const dist = Math.sqrt(dx * dx + dy * dy) || 1
          const force = 800 / (dist * dist)
          const fx = dx / dist * force
          const fy = dy / dist * force
          nodes[i].vx -= fx
          nodes[i].vy -= fy
          nodes[j].vx += fx
          nodes[j].vy += fy
        }
      }

      // Attraction along links
      links.forEach(link => {
        const source = nodeMap[link.source] || nodeMap[link.source?.id]
        const target = nodeMap[link.target] || nodeMap[link.target?.id]
        if (!source || !target) return
        const dx = target.x - source.x
        const dy = target.y - source.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = (dist - 60) * 0.01
        const fx = dx / dist * force
        const fy = dy / dist * force
        source.vx += fx
        source.vy += fy
        target.vx -= fx
        target.vy -= fy
      })

      // Apply velocity with damping
      nodes.forEach(n => {
        n.vx *= 0.6
        n.vy *= 0.6
        n.x += n.vx
        n.y += n.vy
        if (n._el) n._el.setAttribute('transform', `translate(${n.x},${n.y})`)
      })

      // Update link positions
      const lineEls = g.querySelectorAll('line')
      lineEls.forEach(line => {
        const s = nodeMap[line.dataset.source]
        const t = nodeMap[line.dataset.target]
        if (s && t) {
          line.setAttribute('x1', s.x)
          line.setAttribute('y1', s.y)
          line.setAttribute('x2', t.x)
          line.setAttribute('y2', t.y)
        }
      })
    }

    // Run simulation
    let frame = 0
    const maxFrames = 200
    const animate = () => {
      if (frame < maxFrames) {
        tick()
        frame++
        simulationRef.current = requestAnimationFrame(animate)
      }
    }
    animate()
  }, [graphData, filterType, transform])

  useEffect(() => {
    drawGraph()
    return () => {
      if (simulationRef.current) cancelAnimationFrame(simulationRef.current)
    }
  }, [drawGraph])

  const types = graphData ? [...new Set(graphData.nodes.map(n => n.type))] : []

  const handleZoom = (direction) => {
    setTransform(prev => ({
      ...prev,
      k: Math.max(0.2, Math.min(3, prev.k + direction * 0.3))
    }))
  }

  const handleCenter = () => {
    setTransform({ x: 0, y: 0, k: 1 })
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '0.85rem', fontWeight: 600 }}>
          Knowledge Graph
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          <IconButton size="small" onClick={() => handleZoom(1)} sx={{ color: 'text.secondary' }}>
            <ZoomInIcon fontSize="small" />
          </IconButton>
          <IconButton size="small" onClick={() => handleZoom(-1)} sx={{ color: 'text.secondary' }}>
            <ZoomOutIcon fontSize="small" />
          </IconButton>
          <IconButton size="small" onClick={handleCenter} sx={{ color: 'text.secondary' }}>
            <CenterFocusStrongIcon fontSize="small" />
          </IconButton>
          <IconButton size="small" onClick={load} disabled={loading} sx={{ color: 'primary.main' }}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Box>
      </Box>

      {/* Filter */}
      <Box sx={{ px: 2, py: 0.5, display: 'flex', gap: 0.5, flexWrap: 'wrap', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <Chip label="All" size="small" clickable
          variant={filterType === 'all' ? 'filled' : 'outlined'}
          onClick={() => setFilterType('all')}
          sx={{ fontSize: '0.55rem', height: 18 }} />
        {types.sort().map(t => (
          <Chip key={t} label={t} size="small" clickable
            variant={filterType === t ? 'filled' : 'outlined'}
            onClick={() => setFilterType(t)}
            sx={{
              fontSize: '0.55rem', height: 18,
              bgcolor: filterType === t ? (TYPE_COLORS[t] || '#666') : 'transparent',
              color: filterType === t ? '#000' : (TYPE_COLORS[t] || '#ccc'),
            }} />
        ))}
      </Box>

      {/* Graph SVG */}
      <Box sx={{ flex: 1, position: 'relative', bgcolor: '#080c14' }}>
        {loading && (
          <Box sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }}>
            <CircularProgress size={24} sx={{ color: 'primary.main' }} />
          </Box>
        )}
        <svg ref={svgRef} width="100%" height="100%"
          style={{ display: 'block' }}
          onWheel={(e) => {
            e.preventDefault()
            handleZoom(e.deltaY < 0 ? 0.5 : -0.5)
          }}
        />
        {graphData && (
          <Box sx={{ position: 'absolute', bottom: 8, left: 8 }}>
            <Typography sx={{ fontSize: '0.55rem', color: 'text.secondary' }}>
              {graphData.nodes.length} nodes · {graphData.links.length} edges
            </Typography>
          </Box>
        )}
      </Box>

      {/* Selected node detail */}
      {selectedNode && (
        <Box sx={{
          px: 2, py: 1.5, borderTop: '1px solid rgba(255,255,255,0.06)',
          bgcolor: 'rgba(110, 231, 183, 0.04)', maxHeight: 120, overflow: 'auto',
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography sx={{ fontSize: '0.8rem', fontWeight: 600, color: TYPE_COLORS[selectedNode.type] || '#ccc' }}>
              {selectedNode.name}
            </Typography>
            <Chip label={selectedNode.type} size="small"
              sx={{ fontSize: '0.5rem', height: 16, bgcolor: `${TYPE_COLORS[selectedNode.type] || '#666'}20` }} />
          </Box>
          <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary' }}>
            Source: {selectedNode.source} · ID: {selectedNode.id.substring(0, 30)}...
          </Typography>
          {/* Show connections */}
          {graphData && (
            <Box sx={{ mt: 0.5 }}>
              {graphData.links
                .filter(l => l.source === selectedNode.id || l.target === selectedNode.id ||
                  l.source?.id === selectedNode.id || l.target?.id === selectedNode.id)
                .slice(0, 5)
                .map((l, i) => {
                  const otherId = (l.source === selectedNode.id || l.source?.id === selectedNode.id) ? (l.target?.id || l.target) : (l.source?.id || l.source)
                  const otherNode = graphData.nodes.find(n => n.id === otherId)
                  return (
                    <Typography key={i} sx={{ fontSize: '0.55rem', color: 'text.secondary' }}>
                      → {l.rel_type} → {otherNode?.name || otherId}
                    </Typography>
                  )
                })}
            </Box>
          )}
        </Box>
      )}
    </Box>
  )
}
