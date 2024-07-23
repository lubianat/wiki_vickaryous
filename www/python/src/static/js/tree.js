document.addEventListener("DOMContentLoaded", function () {
  // Initialize a node ID counter
  let i = 0;

  // Create the D3 tree visualization
  fetch('/data')
    .then(response => response.json())
    .then(edges => {
      console.log("Edges:", edges);  // Log edges to debug
      const data = buildHierarchy(edges);
      console.log("Hierarchical Data:", JSON.stringify(data, null, 2));  // Log hierarchical data to debug
      renderTree(data);
    });

  function buildHierarchy(edges) {
    const root = { name: "Root", children: [] };
    const map = { "Root": root };
    const levels = {}; // Track levels of nodes

    // First pass: Identify all nodes and their levels
    edges.forEach(edge => {
      const parent = edge[0];
      const child = edge[1];
      const level = edge[5];
      const qid = edge[2];

      if (!map[parent]) {
        map[parent] = { name: parent, children: [] };
      }

      if (!map[child]) {
        map[child] = { name: child, children: [], qid: qid };
      }

      if (!levels[parent]) {
        levels[parent] = level - 1; // Parent level is one less than the child level
      }

      if (!levels[child]) {
        levels[child] = level;
      }
    });

    // Ensure root level is 0
    levels["Root"] = 0;

    // Second pass: Build the hierarchy
    edges.forEach(edge => {
      const parent = edge[0];
      const child = edge[1];

      if (!map[parent].children.find(c => c.name === child)) {
        map[parent].children.push(map[child]);
      }

      if (levels[parent] === 1 && !root.children.find(c => c.name === parent)) {
        root.children.push(map[parent]);
      }
    });

    console.log("Final Map:", map);  // Log the final map

    return root;
  }

  function renderTree(data) {
    const maxWidth = 800;
    const width = Math.min(window.innerWidth, maxWidth);  // Adjust width based on window size
    const height = 800;  // Adjusted height for more space
    const margin = { top: 20, right: 120, bottom: 20, left: 120 };

    const treeLayout = d3.tree().size([height, width - margin.left - margin.right]);

    const root = d3.hierarchy(data, d => d.children);

    root.x0 = height / 2;
    root.y0 = 0;

    const svg = d3.select("#tree-container").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .call(d3.zoom().on("zoom", function(event) {
      svg.attr("transform", `translate(${event.transform.x}, ${event.transform.y})`);
    }).scaleExtent([1, 1]))  // Prevent zooming by setting scaleExtent to [1, 1]
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);
  
  
    root.children.forEach(collapse); // Collapse all children of root initially

    update(root);

    function update(source) {
      const treeData = treeLayout(root);
      const nodes = treeData.descendants();
      const links = treeData.descendants().slice(1);

      nodes.forEach(d => d.y = d.depth * 180);

      const node = svg.selectAll('g.node')
        .data(nodes, d => d.id || (d.id = ++i));

      const nodeEnter = node.enter().append('g')
        .attr('class', 'node')
        .attr('transform', d => `translate(${source.y0},${source.x0})`)
        .on('click', click);

      nodeEnter.append('circle')
        .attr('class', 'node')
        .attr('r', 1e-6)
        .style("fill", d => d._children ? "lightsteelblue" : "#fff");

      nodeEnter.append('text')
        .attr("dy", ".35em")
        .attr("x", d => d.children || d._children ? -13 : 13)
        .attr("text-anchor", d => d.children || d._children ? "end" : "start")
        .text(d => d.data.name)
        .style("fill", d => !d.children && !d._children ? "blue" : "black")
        .style("cursor", d => !d.children && !d._children ? "pointer" : "default")
        .on("click", (event, d) => {
          if (!d.children && !d._children) {
            window.location.href = `/cell/${d.data.qid}`;  // Use QID for the URL
          }
        })
        .on("mouseover", function(event, d) {
          if (!d.children && !d._children) {
            d3.select(this).style("text-decoration", "underline");
          }
        })
        .on("mouseout", function(event, d) {
          if (!d.children && !d._children) {
            d3.select(this).style("text-decoration", "none");
          }
        });

      const nodeUpdate = nodeEnter.merge(node);

      nodeUpdate.transition()
        .duration(200)
        .attr('transform', d => `translate(${d.y},${d.x})`);

      nodeUpdate.select('circle.node')
        .attr('r', 10)
        .style("fill", d => d._children ? "lightsteelblue" : "#fff")
        .attr('cursor', 'pointer');

      const nodeExit = node.exit().transition()
        .duration(200)
        .attr('transform', d => `translate(${source.y},${source.x})`)
        .remove();

      nodeExit.select('circle')
        .attr('r', 1e-6);

      nodeExit.select('text')
        .style('fill-opacity', 1e-6);

      const link = svg.selectAll('path.link')
        .data(links, d => d.id);

      const linkEnter = link.enter().insert('path', "g")
        .attr("class", "link")
        .attr('d', d => {
          const o = { x: source.x0, y: source.x0 };
          return diagonal(o, o);
        })
        .style("stroke", "lightblue")
        .style("stroke-width", 2)
        .style("fill", "lightblue")
        .style("opacity", 0.5);

      const linkUpdate = linkEnter.merge(link);

      linkUpdate.transition()
        .duration(200)
        .attr('d', d => diagonal(d, d.parent))
        .style("stroke", "lightblue")
        .style("opacity", 0.5);

      const linkExit = link.exit().transition()
        .duration(200)
        .attr('d', d => {
          const o = { x: source.x, y: source.y };
          return diagonal(o, o);
        })
        .remove();

      nodes.forEach(d => {
        d.x0 = d.x;
        d.y0 = d.y;
      });

      function diagonal(s, d) {
        return `M ${s.y} ${s.x}
                C ${(s.y + d.y) / 2} ${s.x},
                  ${(s.y + d.y) / 2} ${d.x},
                  ${d.y} ${d.x}`;
      }

      function click(event, d) {
        if (d.children) {
          d._children = d.children;
          d.children = null;
        } else {
          d.children = d._children;
          d._children = null;
        }
        update(d);
      }
    }

    function collapse(d) {
      if (d.children) {
        d._children = d.children;
        d._children.forEach(collapse);
        d.children = null;
      }
    }
  }
});
