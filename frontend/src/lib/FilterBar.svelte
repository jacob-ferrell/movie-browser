<script>
  let { activeTab, onchange } = $props()

  const tabs = [
    { id: 'trending', label: 'Trending' },
    { id: 'movies',   label: 'Movies' },
    { id: 'tv',       label: 'TV Shows' },
  ]
</script>

<div class="flex gap-1 bg-gray-900 rounded-xl p-1 border border-gray-800">
  {#each tabs as tab}
    <button
      class="flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150 {activeTab === tab.id
        ? 'bg-teal-600 text-white shadow'
        : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'}"
      onclick={() => onchange(tab.id)}
    >
      {tab.label}
    </button>
  {/each}
</div>
