// DrugMind 微信小程序 - App.js
App({
  globalData: {
    baseUrl: 'https://43.128.114.201:8096',
    token: null,
    userInfo: null
  },

  onLaunch() {
    const token = wx.getStorageSync('drugmind_token');
    if (token) this.globalData.token = token;
  },

  request(path, options = {}) {
    const url = this.globalData.baseUrl + path;
    const header = { 'Content-Type': 'application/json' };
    if (this.globalData.token) {
      header['Authorization'] = `Bearer ${this.globalData.token}`;
    }
    return new Promise((resolve, reject) => {
      wx.request({
        url, header,
        method: options.method || 'GET',
        data: options.data,
        success: res => res.statusCode === 200 ? resolve(res.data) : reject(res),
        fail: reject
      });
    });
  }
})
