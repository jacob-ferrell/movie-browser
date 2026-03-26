<script>
  import { onMount } from 'svelte'
  import { listFiles, deleteFiles, renameFile, moveFiles, deleteTorrents, fetchDiskUsage } from './api.js'

  const ROOT = '/hdd'

  let { path = ROOT } = $props()

  let disk = $state(null)         // {total, used, free}
  let cwd = $state(ROOT)
  let entries = $state([])
  let loading = $state(false)
  let loadError = $state(null)

  // Selection
  let selected = $state(new Set())  // Set of full paths
  let allSelected = $derived(entries.length > 0 && selected.size === entries.length)
  let someSelected = $derived(selected.size > 0)

  // Rename
  let renamingPath = $state(null)
  let renameValue = $state('')
  let renameError = $state(null)
  let renaming = $state(false)

  // Delete
  let confirmDelete = $state(false)
  let deleteWithTorrent = $state(false)
  let deleting = $state(false)
  let deleteError = $state(null)

  // Move modal
  let moveOpen = $state(false)
  let moveCwd = $state(ROOT)
  let moveEntries = $state([])
  let moveLoading = $state(false)
  let moveError = $state(null)
  let moving = $state(false)

  // Derived: selected entries that have a torrent_hash (for delete dialog)
  let selectedTorrentHashes = $derived(
    entries
      .filter(e => selected.has(e.path) && e.torrent_hash)
      .map(e => e.torrent_hash)
  )

  // Breadcrumbs for main view
  let breadcrumbs = $derived.by(() => {
    const parts = cwd.replace(/\/$/, '').split('/').filter(Boolean)
    return parts.map((name, i) => ({
      name,
      path: '/' + parts.slice(0, i + 1).join('/'),
    }))
  })

  // Breadcrumbs for move modal
  let moveBreadcrumbs = $derived.by(() => {
    const parts = moveCwd.replace(/\/$/, '').split('/').filter(Boolean)
    return parts.map((name, i) => ({
      name,
      path: '/' + parts.slice(0, i + 1).join('/'),
    }))
  })

  function fmtSize(bytes) {
    if (bytes == null) return '—'
    if (bytes >= 1e12) return (bytes / 1e12).toFixed(1) + ' TB'
    if (bytes >= 1e9) return (bytes / 1e9).toFixed(1) + ' GB'
    if (bytes >= 1e6) return (bytes / 1e6).toFixed(1) + ' MB'
    if (bytes >= 1e3) return (bytes / 1e3).toFixed(0) + ' KB'
    return bytes + ' B'
  }

  function fmtDate(ts) {
    return new Date(ts * 1000).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
  }

  async function load(dir = cwd) {
    loading = true
    loadError = null
    selected = new Set()
    renamingPath = null
    try {
      const data = await listFiles(dir)
      cwd = data.path
      entries = data.entries
      const newHash = '#/files?path=' + encodeURIComponent(data.path)
      if (window.location.hash !== newHash) {
        window.history.pushState(null, '', newHash)
      }
    } catch (e) {
      loadError = e.message
    } finally {
      loading = false
    }
  }

  function enter(entry) {
    if (entry.is_dir) load(entry.path)
  }

  function goUp() {
    if (cwd === ROOT) return
    load(cwd.substring(0, cwd.lastIndexOf('/')) || ROOT)
  }

  function toggleSelect(path) {
    const next = new Set(selected)
    if (next.has(path)) next.delete(path)
    else next.add(path)
    selected = next
  }

  function toggleAll() {
    selected = allSelected ? new Set() : new Set(entries.map(e => e.path))
  }

  // --- Rename ---
  function startRename() {
    const path = [...selected][0]
    const entry = entries.find(e => e.path === path)
    if (!entry) return
    renamingPath = path
    renameValue = entry.name
    renameError = null
  }

  function cancelRename() {
    renamingPath = null
    renameError = null
  }

  async function commitRename() {
    if (!renamingPath || !renameValue.trim()) return
    renaming = true
    renameError = null
    try {
      await renameFile(renamingPath, renameValue.trim())
      renamingPath = null
      selected = new Set()
      await load()
    } catch (e) {
      renameError = e.message
    } finally {
      renaming = false
    }
  }

  function handleRenameKey(e) {
    if (e.key === 'Enter') commitRename()
    if (e.key === 'Escape') cancelRename()
  }

  // --- Delete ---
  function openDelete() {
    deleteError = null
    deleteWithTorrent = false
    confirmDelete = true
  }

  async function handleDelete() {
    deleting = true
    deleteError = null
    try {
      const paths = [...selected]
      await deleteFiles(paths)
      if (deleteWithTorrent && selectedTorrentHashes.length > 0) {
        await deleteTorrents(selectedTorrentHashes, false)
      }
      selected = new Set()
      deleteWithTorrent = false
      confirmDelete = false
      await load()
    } catch (e) {
      deleteError = e.message
    } finally {
      deleting = false
    }
  }

  // --- Move ---
  async function openMove() {
    moveError = null
    moveCwd = cwd
    moveOpen = true
    await loadMoveDir(cwd)
  }

  async function loadMoveDir(path) {
    moveLoading = true
    try {
      const data = await listFiles(path)
      moveCwd = data.path
      moveEntries = data.entries.filter(e => e.is_dir)
    } catch (e) {
      moveError = e.message
    } finally {
      moveLoading = false
    }
  }

  async function handleMove() {
    if (moveCwd === cwd) return
    moving = true
    moveError = null
    try {
      await moveFiles([...selected], moveCwd)
      selected = new Set()
      moveOpen = false
      await load()
    } catch (e) {
      moveError = e.message
    } finally {
      moving = false
    }
  }

  onMount(() => {
    load(path)
    fetchDiskUsage().then(d => disk = d).catch(() => {})

    function onPopstate() {
      const params = new URLSearchParams(window.location.hash.replace(/^#[^?]*\??/, ''))
      load(params.get('path') || ROOT)
    }
    window.addEventListener('popstate', onPopstate)
    return () => window.removeEventListener('popstate', onPopstate)
  })
</script>

<div class="max-w-4xl mx-auto py-6 flex flex-col gap-5 {someSelected ? 'pb-24' : ''}">
  <!-- Header: back + breadcrumb -->
  <div class="flex items-center gap-3">
    <button
      onclick={goUp}
      disabled={cwd === ROOT || loading}
      class="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      Back
    </button>
    <div class="h-4 w-px bg-gray-700"></div>
    <!-- Breadcrumb -->
    <div class="flex items-center gap-1 text-sm text-gray-400 min-w-0 flex-wrap">
      {#each breadcrumbs as crumb, i}
        {#if i > 0}<span class="text-gray-700">/</span>{/if}
        <button
          onclick={() => load(crumb.path)}
          class="hover:text-gray-100 transition truncate max-w-[160px] {i === breadcrumbs.length - 1 ? 'text-gray-100 font-medium' : ''}"
        >
          {crumb.name}
        </button>
      {/each}
    </div>
  </div>

  <!-- Disk usage widget -->
  {#if disk}
    {@const usedPct = disk.used / disk.total}
    {@const barColor = usedPct > 0.9 ? 'bg-red-500' : usedPct > 0.75 ? 'bg-amber-500' : 'bg-teal-500'}
    <div class="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 flex items-center gap-4">
      <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 shrink-0 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 12H3a9 9 0 1018 0h-2M12 3v9" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 21h6" />
      </svg>
      <div class="flex-1 flex flex-col gap-1.5 min-w-0">
        <div class="flex items-baseline justify-between gap-2">
          <span class="text-xs text-gray-400">
            <span class="text-gray-200 font-medium">{fmtSize(disk.used)}</span> used of {fmtSize(disk.total)}
          </span>
          <span class="text-xs text-gray-500 shrink-0">{fmtSize(disk.free)} free</span>
        </div>
        <div class="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
          <div class="h-full rounded-full transition-all duration-500 {barColor}" style="width: {(usedPct * 100).toFixed(1)}%"></div>
        </div>
      </div>
    </div>
  {/if}

  {#if loadError}
    <div class="bg-red-900/20 border border-red-800 rounded-xl p-4 text-red-400 text-sm">{loadError}</div>

  {:else if loading}
    <div class="flex flex-col gap-2">
      {#each Array(6) as _}
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-4 animate-pulse h-14"></div>
      {/each}
    </div>

  {:else if entries.length === 0}
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center text-gray-600 text-sm">
      Empty directory
    </div>

  {:else}
    <!-- Select-all bar -->
    <div class="flex items-center gap-3 pl-9">
      <button onclick={toggleAll} class="text-sm text-gray-400 hover:text-gray-200 transition select-none">
        {allSelected ? 'Deselect all' : 'Select all'}
      </button>
      {#if someSelected}
        <span class="text-xs text-gray-500">{selected.size} selected</span>
      {/if}
    </div>

    <!-- Entry list -->
    <div class="flex flex-col gap-2">
      {#each entries as entry (entry.path)}
        {@const isSelected = selected.has(entry.path)}
        {@const isRenaming = renamingPath === entry.path}
        <div class="flex items-center gap-2">
          <!-- Circular toggle -->
          <button
            onclick={() => toggleSelect(entry.path)}
            class="shrink-0 w-7 h-7 rounded-full flex items-center justify-center transition
              {isSelected
                ? 'bg-teal-500 text-white'
                : 'bg-gray-800 border border-gray-600 text-transparent hover:border-gray-400'}"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
            </svg>
          </button>

          <!-- Entry card -->
          <div
            class="flex-1 bg-gray-900 border rounded-xl px-4 py-3 flex items-center gap-3 transition
              {isSelected ? 'border-teal-600/60' : 'border-gray-800'}"
          >
            <!-- Icon -->
            <span class="shrink-0 text-base {entry.is_dir ? 'text-teal-500' : 'text-gray-600'}">
              {#if entry.is_dir}
                <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
                </svg>
              {:else}
                <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              {/if}
            </span>

            <!-- Name (or rename input) -->
            <div class="flex-1 min-w-0">
              {#if isRenaming}
                <input
                  type="text"
                  bind:value={renameValue}
                  onkeydown={handleRenameKey}
                  onblur={commitRename}
                  autofocus
                  class="w-full bg-gray-800 border border-teal-500 rounded px-2 py-0.5 text-sm text-gray-100 focus:outline-none font-mono"
                />
                {#if renameError}
                  <p class="text-red-400 text-xs mt-0.5">{renameError}</p>
                {/if}
              {:else}
                <button
                  onclick={() => entry.is_dir && enter(entry)}
                  class="text-sm font-medium text-gray-100 truncate text-left w-full {entry.is_dir ? 'hover:text-teal-400 cursor-pointer' : 'cursor-default'} transition"
                  title={entry.name}
                >
                  {entry.name}
                </button>
              {/if}
            </div>

            <!-- Torrent badge -->
            {#if entry.torrent_hash}
              <span class="shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-teal-700/40 text-teal-400">
                torrent
              </span>
            {/if}

            <!-- Size + date -->
            <div class="shrink-0 text-right flex flex-col items-end gap-0.5">
              <span class="text-xs text-gray-400 font-mono">{fmtSize(entry.size)}</span>
              <span class="text-[10px] text-gray-600">{fmtDate(entry.modified)}</span>
            </div>

            <!-- Drill-in arrow for dirs -->
            {#if entry.is_dir && !isRenaming}
              <button
                onclick={() => enter(entry)}
                class="shrink-0 text-gray-600 hover:text-teal-500 transition"
                title="Open folder"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Floating action bar -->
{#if someSelected}
  <div class="fixed bottom-6 left-1/2 -translate-x-1/2 z-30 flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 shadow-2xl shadow-black/60">
    <span class="text-sm text-gray-300 font-medium pr-2 border-r border-gray-700">
      {selected.size} selected
    </span>
    {#if selected.size === 1}
      <button
        onclick={startRename}
        class="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs font-medium text-gray-200 transition"
      >
        Rename
      </button>
    {/if}
    <button
      onclick={openMove}
      class="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs font-medium text-gray-200 transition"
    >
      Move
    </button>
    <button
      onclick={openDelete}
      class="px-3 py-1.5 bg-red-700 hover:bg-red-600 rounded-lg text-xs font-medium text-white transition"
    >
      Delete {selected.size === 1 ? '1 item' : `${selected.size} items`}
    </button>
  </div>
{/if}

<!-- Delete confirmation dialog -->
{#if confirmDelete}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
    onclick={() => { if (!deleting) confirmDelete = false }}
  >
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div
      class="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-sm mx-4 flex flex-col gap-4 shadow-2xl"
      onclick={e => e.stopPropagation()}
    >
      <h3 class="text-base font-semibold text-gray-100">
        Delete {selected.size === 1 ? '1 item' : `${selected.size} items`}?
      </h3>
      <p class="text-sm text-gray-400">
        Files will be permanently deleted from disk. This cannot be undone.
      </p>

      {#if selectedTorrentHashes.length > 0}
        <button
          onclick={() => deleteWithTorrent = !deleteWithTorrent}
          class="flex items-center gap-3 select-none bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-left transition hover:border-gray-600"
        >
          <span class="shrink-0 w-7 h-7 rounded-full flex items-center justify-center transition
            {deleteWithTorrent ? 'bg-teal-500 text-white' : 'bg-gray-700 border border-gray-600 text-transparent'}">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
            </svg>
          </span>
          <div class="flex flex-col">
            <span class="text-sm text-gray-200 font-medium">Also remove from qBittorrent</span>
            <span class="text-xs text-gray-500">
              {selectedTorrentHashes.length === 1 ? 'Removes the associated torrent' : `Removes ${selectedTorrentHashes.length} associated torrents`}
            </span>
          </div>
        </button>
      {/if}

      {#if deleteError}
        <p class="text-red-400 text-xs">{deleteError}</p>
      {/if}

      <div class="flex gap-3 justify-end">
        <button
          onclick={() => confirmDelete = false}
          disabled={deleting}
          class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 disabled:opacity-40 transition"
        >
          Cancel
        </button>
        <button
          onclick={handleDelete}
          disabled={deleting}
          class="px-4 py-2 bg-red-700 hover:bg-red-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm font-medium text-white transition"
        >
          {deleting ? 'Deleting…' : 'Delete'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Move modal -->
{#if moveOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
    onclick={() => { if (!moving) moveOpen = false }}
  >
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div
      class="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md mx-4 flex flex-col gap-4 shadow-2xl"
      onclick={e => e.stopPropagation()}
    >
      <h3 class="text-base font-semibold text-gray-100">Move to…</h3>

      <!-- Modal breadcrumb -->
      <div class="flex items-center gap-1 text-xs text-gray-400 flex-wrap">
        {#each moveBreadcrumbs as crumb, i}
          {#if i > 0}<span class="text-gray-700">/</span>{/if}
          <button
            onclick={() => loadMoveDir(crumb.path)}
            class="hover:text-gray-100 transition {i === moveBreadcrumbs.length - 1 ? 'text-gray-200 font-medium' : ''}"
          >
            {crumb.name}
          </button>
        {/each}
      </div>

      <!-- Folder list -->
      <div class="flex flex-col gap-1 overflow-y-auto max-h-56 border border-gray-800 rounded-lg p-1">
        {#if moveLoading}
          <div class="py-6 text-center text-xs text-gray-600">Loading…</div>
        {:else if moveEntries.length === 0}
          <div class="py-6 text-center text-xs text-gray-600">No subfolders</div>
        {:else}
          {#each moveEntries as e}
            <button
              onclick={() => loadMoveDir(e.path)}
              class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-200 hover:bg-gray-800 text-left transition"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-teal-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
              </svg>
              {e.name}
            </button>
          {/each}
        {/if}
      </div>

      <p class="text-xs text-gray-500">
        Destination: <span class="text-gray-300 font-mono">{moveCwd}</span>
      </p>

      {#if moveError}
        <p class="text-red-400 text-xs">{moveError}</p>
      {/if}

      <div class="flex gap-3 justify-end">
        <button
          onclick={() => moveOpen = false}
          disabled={moving}
          class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 disabled:opacity-40 transition"
        >
          Cancel
        </button>
        <button
          onclick={handleMove}
          disabled={moving || moveCwd === cwd}
          class="px-4 py-2 bg-teal-600 hover:bg-teal-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm font-medium text-white transition"
        >
          {moving ? 'Moving…' : 'Move Here'}
        </button>
      </div>
    </div>
  </div>
{/if}
