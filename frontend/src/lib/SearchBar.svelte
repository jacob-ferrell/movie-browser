<script>
  let { value = $bindable(''), onSearch } = $props()

  let timer

  function handleInput(e) {
    value = e.target.value
    clearTimeout(timer)
    timer = setTimeout(() => onSearch(value), 300)
  }

  function clear() {
    value = ''
    onSearch('')
  }
</script>

<div class="relative w-full max-w-md">
  <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none">
    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  </span>
  <input
    type="search"
    placeholder="Search movies & shows..."
    value={value}
    oninput={handleInput}
    class="w-full bg-gray-900 border border-gray-700 rounded-xl pl-9 pr-9 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition"
  />
  {#if value}
    <button
      onclick={clear}
      class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
      aria-label="Clear search"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  {/if}
</div>
