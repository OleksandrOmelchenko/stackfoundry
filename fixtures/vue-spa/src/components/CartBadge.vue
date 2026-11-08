<script setup lang="ts">
import { computed } from "vue";

interface CartItem {
  id: string;
  quantity: number;
}

const props = defineProps<{ items: CartItem[] }>();

const count = computed(() => props.items.length);
</script>

<template>
  <span v-if="count > 0" class="cart-badge" aria-label="Items in cart">{{ count }}</span>
</template>
