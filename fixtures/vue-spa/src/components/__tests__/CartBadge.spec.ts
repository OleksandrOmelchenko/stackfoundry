import { mount } from "@vue/test-utils";
import CartBadge from "../CartBadge.vue";

describe("CartBadge", () => {
  it("renders", () => {
    const wrapper = mount(CartBadge, { props: { items: [{ id: "a", quantity: 2 }] } });
    expect(wrapper).toBeTruthy();
  });
});
