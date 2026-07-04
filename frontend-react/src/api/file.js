import apiClient from './index'

/**
 * 文件相关 API。
 *
 * 复用 src/api/index.js 的 axios 客户端。
 *
 * 本项目已配置 TOKEN_VALIDATION_ENABLED=false，后端不读 jwt header，
 * 因此不需要在请求里手动注入 token。
 */
export const fileApi = {
  /**
   * 物理删除文件（DELETE /files/{file_uuid}）。
   *
   * 后端返回 amis 格式：{ status: 0, msg: 'ok', data: { file_id } }。
   * 404（已不存在）视为成功（幂等）。
   *
   * @param {string} fileId - 后端 UploadedFile.file_uuid
   * @returns {Promise<{status: number, msg: string, data: {file_id: string}}>}
   */
  delete: (fileId) => apiClient.delete(`/files/${fileId}`),
}
