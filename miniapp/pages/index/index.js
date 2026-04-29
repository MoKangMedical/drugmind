const app = getApp();
Page({
  data: { discussions: [], roles: [] },
  onLoad() {
    app.request('/api/v2/hub').then(res => this.setData({ discussions: res.discussions }));
    app.request('/api/v2/roles').then(res => this.setData({ roles: res.roles }));
  },
  goDiscuss() { wx.switchTab({ url: '/pages/discuss/discuss' }); },
  goAsk() { wx.switchTab({ url: '/pages/ask/ask' }); },
  goDetail(e) {
    wx.navigateTo({ url: `/pages/discuss/detail?id=${e.currentTarget.dataset.id}` });
  }
})
