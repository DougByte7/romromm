import { createApp } from "vue";
import App from "@/RomM.vue";
import "@/console/index.css";
import { registerPlugins } from "@/plugins";
import router from "@/plugins/router";
import storeAuth from "@/stores/auth";
import storeConfig from "@/stores/config";
import storeHeartbeat from "@/stores/heartbeat";
import storeTasks from "@/stores/tasks";
import "@/styles/common.css";
import "@/styles/fonts.css";
import "@/styles/scrollbar.css";

async function initializeData() {
  const heartbeatStore = storeHeartbeat();
  const authStore = storeAuth();
  const configStore = storeConfig();
  const tasksStore = storeTasks();

  // Load heartbeat first to decide whether setup wizard is active.
  await heartbeatStore.fetchHeartbeat();

  if (heartbeatStore.value.SYSTEM.SHOW_SETUP_WIZARD) {
    await configStore.fetchConfig();
    authStore.reset();
    return;
  }

  // Load remaining initial data only when setup wizard is not active.
  await Promise.all([
    authStore.fetchCurrentUser(),
    configStore.fetchConfig(),
    tasksStore.fetchTasks(),
  ]);
}

async function initializeApp() {
  const app = createApp(App);

  // Registrar vuetify + pinia + i18n + emitter
  registerPlugins(app);

  await initializeData();

  app.use(router);

  app.mount("#app");
}

initializeApp();
