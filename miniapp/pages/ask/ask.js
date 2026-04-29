const app = getApp();
Page({
  data: {
    roles: [],
    question: '',
    context: '',
    responses: [],
    loading: false
  },
  onLoad() {
    app.request('/api/v2/roles').then(res => {
      this.setData({ roles: res.roles.map(r => ({ ...r, selected: true })) });
    });
  },
  toggleRole(e) {
    const idx = e.currentTarget.dataset.index;
    const roles = this.data.roles;
    roles[idx].selected = !roles[idx].selected;
    this.setData({ roles });
  },
  onInput(e) { this.setData({ question: e.detail.value }); },
  onContextInput(e) { this.setData({ context: e.detail.value }); },
  submitAsk() {
    if (!this.data.question.trim()) {
      wx.showToast({ title: '请输入问题', icon: 'none' });
      return;
    }
    this.setData({ loading: true, responses: [] });
    const roles = this.data.roles.filter(r => r.selected).map(r => r.role_id);
    app.request('/api/v2/quick-ask', {
      method: 'POST',
      data: { question: this.data.question, roles, context: this.data.context }
    }).then(res => {
      this.setData({ responses: res.responses, loading: false });
    }).catch(() => {
      wx.showToast({ title: '请求失败', icon: 'none' });
      this.setData({ loading: false });
    });
  }
})
