(() => {
  "use strict";

  const root = document.querySelector("#route-map");
  if (!root) return;

  const SVG_NS = "http://www.w3.org/2000/svg";
  const MAP_WIDTH = 1020;
  const MAP_HEIGHT = 720;
  const DEFAULT_BOUNDS = {
    east_min: -6,
    east_max: 96,
    north_min: -6,
    north_max: 66,
  };
  const DEFAULT_LEVELS = ["B1", "B2", "B3"];
  const STATUS_COLORS = {
    available: "#8fa874",
    occupied: "#686963",
    reserved: "#b96952",
  };

  const elements = {
    base: document.querySelector("#route-map-base"),
    route: document.querySelector("#route-map-route"),
    overlay: document.querySelector("#route-map-overlay"),
    empty: document.querySelector("#route-map-empty"),
    floorTabs: document.querySelector("#route-map-floor-tabs"),
    liveState: document.querySelector("#route-map-live-state"),
    distance: document.querySelector("#route-map-distance"),
    eta: document.querySelector("#route-map-eta"),
    destination: document.querySelector("#route-map-destination"),
    locate: document.querySelector("#route-map-locate"),
  };

  const state = {
    mapData: null,
    route: null,
    spotId: null,
    activeLevel: "B1",
    bounds: DEFAULT_BOUNDS,
    watchId: null,
    refreshTimer: null,
    lastLocation: null,
    lastRouteRefreshAt: 0,
    refreshing: false,
    loadingMap: null,
    floorSelectedByUser: false,
  };

  function svgNode(name, attributes = {}) {
    const node = document.createElementNS(SVG_NS, name);
    for (const [key, value] of Object.entries(attributes)) {
      node.setAttribute(key, String(value));
    }
    return node;
  }

  function addSvgText(parent, text, x, y, attributes = {}) {
    const node = svgNode("text", { x, y, ...attributes });
    node.textContent = text;
    parent.append(node);
    return node;
  }

  function px(x) {
    const bounds = state.bounds;
    return (
      (x - bounds.east_min)
      / (bounds.east_max - bounds.east_min)
      * MAP_WIDTH
    );
  }

  function py(y) {
    const bounds = state.bounds;
    return (
      (bounds.north_max - y)
      / (bounds.north_max - bounds.north_min)
      * MAP_HEIGHT
    );
  }

  function levelData(level) {
    return state.mapData?.levels?.find((item) => item.id === level);
  }

  function routeLevels() {
    if (!state.route?.path) return new Set();
    return new Set(state.route.path.map((node) => node.level));
  }

  function setLiveState(text, mode = "idle") {
    elements.liveState.classList.toggle("is-live", mode === "live");
    elements.liveState.classList.toggle("is-warning", mode === "warning");
    const label = elements.liveState.querySelector("span");
    if (label) label.textContent = text;
  }

  function formatDistance(distance) {
    const value = Number(distance);
    if (!Number.isFinite(value)) return "--";
    return value < 1000
      ? `${Math.round(value)} m`
      : `${(value / 1000).toFixed(1)} km`;
  }

  function formatEta(seconds) {
    const value = Number(seconds);
    if (!Number.isFinite(value)) return "--";
    if (value < 60) return `${Math.round(value)} 秒`;
    return `${Math.max(1, Math.round(value / 60))} 分钟`;
  }

  function updateReadout() {
    elements.distance.textContent = formatDistance(
      state.route?.distance_m,
    );
    elements.eta.textContent = formatEta(
      state.route?.estimated_drive_seconds,
    );
    elements.destination.textContent =
      state.route?.destination?.label || "等待导航";
  }

  function drawFloorShell(level) {
    elements.base.replaceChildren();

    const shell = svgNode("g", { class: "map-floor-shell" });
    shell.append(svgNode("rect", {
      x: px(0),
      y: py(65),
      width: px(95) - px(0),
      height: py(0) - py(65),
      rx: 28,
      class: "map-floor-background",
    }));
    elements.base.append(shell);

    const grid = svgNode("g", { class: "map-floor-grid" });
    for (let east = 10; east < 95; east += 10) {
      grid.append(svgNode("line", {
        x1: px(east),
        y1: py(0),
        x2: px(east),
        y2: py(65),
      }));
    }
    for (let north = 10; north < 65; north += 10) {
      grid.append(svgNode("line", {
        x1: px(0),
        y1: py(north),
        x2: px(95),
        y2: py(north),
      }));
    }
    shell.append(grid);

    const zones = state.mapData?.zones || [];
    const zoneGroup = svgNode("g", { class: "map-zones" });
    for (const zone of zones) {
      zoneGroup.append(svgNode("rect", {
        x: px(zone.east_min),
        y: py(zone.north_max),
        width: px(zone.east_max) - px(zone.east_min),
        height: py(zone.north_min) - py(zone.north_max),
        rx: 16,
        class: `map-zone map-zone-${zone.id.toLowerCase()}`,
      }));
      addSvgText(
        zoneGroup,
        zone.label,
        px(zone.east_min) + 18,
        py(zone.north_max) + 34,
        { class: "map-zone-label" },
      );
    }
    shell.append(zoneGroup);

    addSvgText(
      shell,
      `${level} / INDOOR`,
      px(0) + 24,
      py(0) - 18,
      { class: "map-floor-label" },
    );
    addSvgText(
      shell,
      "ENTRY",
      px(0) + 20,
      py(0) + 31,
      { class: "map-entry-label" },
    );
  }

  function drawNetwork(level) {
    const data = levelData(level);
    if (!data) return;

    const nodeMap = new Map(
      data.nodes.map((node) => [node.id, node]),
    );
    const network = svgNode("g", { class: "map-network" });
    for (const edge of data.edges) {
      const from = nodeMap.get(edge.from);
      const to = nodeMap.get(edge.to);
      if (!from || !to) continue;
      const isRamp = edge.kind === "ramp";
      network.append(svgNode("line", {
        x1: px(from.x_m),
        y1: py(from.y_m),
        x2: px(to.x_m),
        y2: py(to.y_m),
        class: isRamp ? "map-lane is-ramp" : "map-lane",
      }));
    }
    elements.base.append(network);

    const spots = svgNode("g", { class: "map-spots" });
    for (const spot of data.spots) {
      const spotNode = svgNode("g", {
        class: `map-spot is-${spot.status}`,
        transform: `translate(${px(spot.x_m)} ${py(spot.y_m)})`,
      });
      spotNode.append(svgNode("circle", {
        r: spot.id === state.spotId ? 10 : 6,
        fill: STATUS_COLORS[spot.status] || STATUS_COLORS.occupied,
      }));
      const title = svgNode("title");
      title.textContent = `${spot.label} · ${spot.status}`;
      spotNode.append(title);
      spots.append(spotNode);
    }
    elements.base.append(spots);
  }

  function drawRoute(level) {
    elements.route.replaceChildren();
    elements.overlay.replaceChildren();
    if (!state.route?.path?.length) return;

    const segments = [];
    let current = [];
    for (const node of state.route.path) {
      if (node.level === level) {
        current.push(node);
      } else if (current.length) {
        segments.push(current);
        current = [];
      }
    }
    if (current.length) segments.push(current);

    const routeGroup = svgNode("g", { class: "map-route-lines" });
    for (const segment of segments) {
      const points = segment
        .map((node) => `${px(node.x_m)},${py(node.y_m)}`)
        .join(" ");
      if (segment.length > 1) {
        routeGroup.append(svgNode("polyline", {
          points,
          class: "map-route-halo",
        }));
        routeGroup.append(svgNode("polyline", {
          points,
          class: "map-route-line",
          "marker-end": "url(#routeArrow)",
        }));
      }
    }
    elements.route.append(routeGroup);

    for (let index = 0; index < state.route.path.length - 1; index += 1) {
      const from = state.route.path[index];
      const to = state.route.path[index + 1];
      if (from.level !== level || from.level === to.level) continue;
      const marker = svgNode("g", {
        class: "map-floor-jump",
        transform: `translate(${px(from.x_m)} ${py(from.y_m)})`,
      });
      marker.append(svgNode("circle", { r: 14 }));
      addSvgText(marker, "↓", 0, 5, {
        "text-anchor": "middle",
      });
      elements.overlay.append(marker);
      addSvgText(
        elements.overlay,
        `坡道前往 ${to.level}`,
        px(from.x_m) - 172,
        py(from.y_m) - 20,
        { class: "map-jump-label" },
      );
    }

    const start = state.route.start;
    if (start?.level === level) {
      const startMarker = svgNode("g", {
        class: "map-start-marker",
        transform: `translate(${px(start.x_m)} ${py(start.y_m)})`,
      });
      startMarker.append(svgNode("circle", {
        r: 19,
        class: "map-start-ring",
      }));
      startMarker.append(svgNode("circle", {
        r: 8,
        class: "map-start-dot",
      }));
      addSvgText(startMarker, "起点", 25, 5, {
        class: "map-marker-label",
      });
      elements.overlay.append(startMarker);
    }

    const destination = state.route.destination;
    if (destination?.level === level) {
      const destMarker = svgNode("g", {
        class: "map-destination-marker",
        transform: `translate(${px(destination.x_m)} ${py(destination.y_m)})`,
      });
      destMarker.append(svgNode("circle", {
        r: 21,
        class: "map-destination-ring",
      }));
      destMarker.append(svgNode("circle", {
        r: 9,
        class: "map-destination-dot",
      }));
      addSvgText(destMarker, destination.label, 28, 5, {
        class: "map-marker-label is-destination",
      });
      elements.overlay.append(destMarker);
    }

    addSvgText(
      elements.overlay,
      state.floorSelectedByUser
        ? `正在查看 ${level} 层`
        : `导航起点 · ${level} 层`,
      24,
      MAP_HEIGHT - 21,
      { class: "map-route-note" },
    );
  }

  function renderTabs() {
    const levels = state.mapData?.levels?.map((item) => item.id)
      || DEFAULT_LEVELS;
    const activeRouteLevels = routeLevels();
    elements.floorTabs.replaceChildren();

    for (const level of levels) {
      const data = levelData(level);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "map-floor-tab";
      button.setAttribute("role", "tab");
      button.setAttribute(
        "aria-selected",
        String(level === state.activeLevel),
      );
      button.classList.toggle("is-active", level === state.activeLevel);
      button.classList.toggle("has-route", activeRouteLevels.has(level));
      button.innerHTML = (
        `<strong>${level}</strong>`
        + `<small>${data
          ? `${data.counts.available}/${data.counts.total}`
          : "实时"}</small>`
      );
      button.addEventListener("click", () => {
        state.activeLevel = level;
        state.floorSelectedByUser = true;
        render();
      });
      elements.floorTabs.append(button);
    }
  }

  function render() {
    if (!state.activeLevel) state.activeLevel = "B1";
    drawFloorShell(state.activeLevel);
    drawNetwork(state.activeLevel);
    drawRoute(state.activeLevel);
    renderTabs();
    updateReadout();
  }

  async function loadMapData(silent = false) {
    if (state.loadingMap) return state.loadingMap;
    state.loadingMap = (async () => {
      try {
        const response = await fetch("/parking/map", {
          cache: "no-store",
        });
        if (!response.ok) throw new Error("地图数据暂不可用");
        const data = await response.json();
        state.mapData = data;
        state.bounds = data.bounds || DEFAULT_BOUNDS;
        if (!silent) {
          setLiveState(
            data.is_demo_data ? "实时演示数据" : "地图数据已更新",
            "live",
          );
        }
        render();
        return true;
      } catch (error) {
        if (!silent) {
          setLiveState(error.message || "地图数据暂不可用", "warning");
        }
        render();
        return false;
      } finally {
        state.loadingMap = null;
      }
    })();
    return state.loadingMap;
  }

  async function showRoute(route) {
    if (!route?.path?.length) return false;

    state.route = route;
    state.spotId = route.destination?.spot_id || null;
    state.activeLevel = route.start?.level || state.activeLevel || "B1";
    state.floorSelectedByUser = false;
    elements.empty.hidden = true;
    elements.locate.disabled = false;
    elements.locate.textContent = "更新我的位置";
    updateReadout();
    setLiveState("路线已生成", "live");

    if (!state.mapData) {
      await loadMapData(true);
    }
    render();
    startTracking();
    return true;
  }

  function clearRoute(message = "等待路线") {
    state.route = null;
    state.spotId = null;
    state.floorSelectedByUser = false;
    stopTracking();
    elements.empty.hidden = false;
    elements.locate.disabled = true;
    elements.locate.textContent = "开启实时定位";
    elements.distance.textContent = "--";
    elements.eta.textContent = "--";
    elements.destination.textContent = "等待导航";
    setLiveState(message, "idle");
    render();
  }

  function distanceBetween(first, second) {
    if (!first || !second) return Number.POSITIVE_INFINITY;
    const toRadians = (value) => value * Math.PI / 180;
    const latitudeDelta = toRadians(
      second.latitude - first.latitude,
    );
    const longitudeDelta = toRadians(
      second.longitude - first.longitude,
    );
    const latitude1 = toRadians(first.latitude);
    const latitude2 = toRadians(second.latitude);
    const value = (
      Math.sin(latitudeDelta / 2) ** 2
      + Math.cos(latitude1)
      * Math.cos(latitude2)
      * Math.sin(longitudeDelta / 2) ** 2
    );
    return 6_371_000 * 2 * Math.atan2(
      Math.sqrt(value),
      Math.sqrt(1 - value),
    );
  }

  async function refreshRoute(location, force = false) {
    if (
      !state.spotId
      || state.refreshing
      || (!force && Date.now() - state.lastRouteRefreshAt < 8_000)
    ) {
      return;
    }

    state.refreshing = true;
    setLiveState("正在刷新路线", "live");
    try {
      const params = new URLSearchParams({
        spot_id: state.spotId,
        latitude: String(location.latitude),
        longitude: String(location.longitude),
      });
      const response = await fetch(`/parking/route?${params}`, {
        cache: "no-store",
      });
      if (response.status === 404) {
        clearRoute("目标车位已不可用");
        return;
      }
      if (!response.ok) throw new Error("路线刷新失败");
      state.route = await response.json();
      state.lastRouteRefreshAt = Date.now();
      updateReadout();
      render();
      setLiveState("实时定位已更新", "live");
    } catch {
      setLiveState("定位正常，路线待重试", "warning");
    } finally {
      state.refreshing = false;
    }
  }

  function handlePosition(position) {
    const nextLocation = {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
    };
    const moved = distanceBetween(state.lastLocation, nextLocation);
    state.lastLocation = nextLocation;
    elements.locate.textContent = "定位已连接";
    setLiveState("实时定位中", "live");

    if (
      moved >= 3
      || Date.now() - state.lastRouteRefreshAt >= 12_000
    ) {
      refreshRoute(nextLocation);
    }
  }

  function handleLocationError(error) {
    const denied = error?.code === 1;
    setLiveState(
      denied
        ? "定位权限未开启 · 按入口规划"
        : "定位暂不可用 · 按入口规划",
      "warning",
    );
    elements.locate.textContent = "重新定位";
    if (denied && state.watchId !== null) {
      navigator.geolocation.clearWatch(state.watchId);
      state.watchId = null;
    }
  }

  function startRefreshLoop() {
    if (state.refreshTimer !== null) return;
    const refreshSeconds = (
      state.mapData?.refresh_after_seconds
      || state.route?.refresh_after_seconds
      || 10
    );
    state.refreshTimer = window.setInterval(() => {
      if (document.hidden) return;
      loadMapData(true);
      if (state.lastLocation) {
        refreshRoute(state.lastLocation, true);
      }
    }, Math.max(5, refreshSeconds) * 1_000);
  }

  function startTracking() {
    startRefreshLoop();
    if (!state.spotId || state.watchId !== null) return;
    if (!navigator.geolocation) {
      setLiveState("本设备不支持定位 · 按入口规划", "warning");
      return;
    }
    if (!window.isSecureContext) {
      setLiveState("HTTPS 后可持续定位 · 当前按入口", "warning");
      elements.locate.textContent = "需要 HTTPS";
      return;
    }
    state.watchId = navigator.geolocation.watchPosition(
      handlePosition,
      handleLocationError,
      {
        enableHighAccuracy: true,
        maximumAge: 10_000,
        timeout: 12_000,
      },
    );
  }

  function stopTracking() {
    if (state.watchId !== null && navigator.geolocation) {
      navigator.geolocation.clearWatch(state.watchId);
    }
    state.watchId = null;
    state.lastLocation = null;
    if (state.refreshTimer !== null) {
      window.clearInterval(state.refreshTimer);
      state.refreshTimer = null;
    }
  }

  function requestCurrentPosition() {
    if (!state.route || !navigator.geolocation) return;
    if (!window.isSecureContext) {
      setLiveState("实时定位需要 HTTPS 页面", "warning");
      return;
    }
    elements.locate.textContent = "正在定位…";
    navigator.geolocation.getCurrentPosition(
      (position) => {
        handlePosition(position);
        refreshRoute(
          {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          },
          true,
        );
      },
      handleLocationError,
      {
        enableHighAccuracy: true,
        maximumAge: 0,
        timeout: 12_000,
      },
    );
  }

  function focusMap() {
    root.classList.remove("is-focused");
    void root.offsetWidth;
    root.classList.add("is-focused");
    root.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
    window.setTimeout(() => root.classList.remove("is-focused"), 1_800);
  }

  elements.locate.addEventListener("click", requestCurrentPosition);
  elements.locate.disabled = true;
  state.activeLevel = "B1";
  setLiveState("等待路线");
  loadMapData();

  window.NavParkRouteMap = {
    showRoute,
    clearRoute,
    focusMap,
    reload: () => loadMapData(),
  };
  document.documentElement.dataset.navparkRouteMap = "ready";
})();
