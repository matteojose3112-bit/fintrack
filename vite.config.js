import { defineConfig } from "vite";
export default defineConfig({base:"/fintrack/",test:{environment:"node",coverage:{reporter:["text","html"]}}});
